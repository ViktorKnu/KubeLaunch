"""FastAPI backend that forwards prompts to the local Ollama runtime."""

import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field, field_validator

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL", "http://ollama.ollama.svc.cluster.local:11434"
)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "tinyllama")
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))

PROMPT_REQUESTS = Counter(
    "kubelaunch_prompt_requests_total",
    "Number of prompts handled by the AI demo backend.",
    labelnames=("status",),
)
PROMPT_DURATION = Histogram(
    "kubelaunch_prompt_duration_seconds",
    "Time spent waiting for an Ollama prompt response.",
    buckets=(0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120),
)
for metric_status in ("success", "error"):
    PROMPT_REQUESTS.labels(status=metric_status)


class PromptRequest(BaseModel):
    """Prompt accepted from the demo UI or API client."""

    prompt: str = Field(min_length=1, max_length=4000)

    @field_validator("prompt")
    @classmethod
    def prompt_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("prompt must contain text")
        return value


class PromptResponse(BaseModel):
    """Small, stable response shape for the frontend."""

    answer: str
    model: str
    response_time_ms: float


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    timeout = httpx.Timeout(OLLAMA_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=timeout) as client:
        application.state.ollama_client = client
        yield


app = FastAPI(
    title="KubeLaunch AI demo API",
    version="0.1.0",
    lifespan=lifespan,
)


def get_ollama_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.ollama_client


@app.get("/health")
async def health() -> dict[str, str]:
    """Report process health without invoking the model."""
    return {"status": "ok", "model": OLLAMA_MODEL}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Expose Prometheus metrics on the application server."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/prompt", response_model=PromptResponse)
async def prompt(
    payload: PromptRequest,
    client: Annotated[httpx.AsyncClient, Depends(get_ollama_client)],
) -> PromptResponse:
    """Send one non-streaming prompt to Ollama and return its answer."""
    started_at = time.perf_counter()
    metric_status = "error"
    try:
        response = await client.post(
            "/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": payload.prompt,
                "stream": False,
            },
        )
        response.raise_for_status()
        ollama_payload = response.json()
        answer = ollama_payload.get("response")
        if not isinstance(answer, str):
            raise ValueError("Ollama response did not contain text")
        metric_status = "success"
    except httpx.TimeoutException as error:
        raise HTTPException(status_code=504, detail="Ollama timed out") from error
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(status_code=502, detail="Ollama request failed") from error
    finally:
        elapsed_seconds = time.perf_counter() - started_at
        PROMPT_REQUESTS.labels(status=metric_status).inc()
        PROMPT_DURATION.observe(elapsed_seconds)

    return PromptResponse(
        answer=answer,
        model=OLLAMA_MODEL,
        response_time_ms=round(elapsed_seconds * 1000, 1),
    )
