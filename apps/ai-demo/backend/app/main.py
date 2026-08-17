"""FastAPI backend that forwards prompts to a configured AI runtime."""

import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, Field, field_validator

AI_RUNTIME = os.getenv("AI_RUNTIME", "ollama").lower()
AI_RUNTIME_BASE_URL = os.getenv(
    "AI_RUNTIME_BASE_URL",
    os.getenv("OLLAMA_BASE_URL", "http://ollama.ollama.svc.cluster.local:11434"),
)
AI_MODEL = os.getenv("AI_MODEL", os.getenv("OLLAMA_MODEL", "tinyllama"))
AI_TRACK = os.getenv("AI_TRACK", "stable")
AI_TIMEOUT_SECONDS = float(
    os.getenv("AI_TIMEOUT_SECONDS", os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
)
AI_RUNTIME_API_KEY = os.getenv("AI_RUNTIME_API_KEY")
SUPPORTED_RUNTIMES = {"ollama", "vllm"}

if AI_RUNTIME not in SUPPORTED_RUNTIMES:
    raise RuntimeError(f"Unsupported AI runtime: {AI_RUNTIME}")

PROMPT_REQUESTS = Counter(
    "kubelaunch_prompt_requests_total",
    "Number of prompts handled by the AI demo backend.",
    labelnames=("status", "model", "runtime", "track"),
)
PROMPT_DURATION = Histogram(
    "kubelaunch_prompt_duration_seconds",
    "Time spent waiting for an AI runtime prompt response.",
    labelnames=("model", "runtime", "track"),
    buckets=(0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120),
)
PROMPT_IN_PROGRESS = Gauge(
    "kubelaunch_prompt_requests_in_progress",
    "Number of prompts currently waiting for an AI runtime response.",
    labelnames=("model", "runtime", "track"),
)
METRIC_LABELS = {
    "model": AI_MODEL,
    "runtime": AI_RUNTIME,
    "track": AI_TRACK,
}
for metric_status in ("success", "error"):
    PROMPT_REQUESTS.labels(status=metric_status, **METRIC_LABELS)


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
    timeout = httpx.Timeout(AI_TIMEOUT_SECONDS)
    headers = {}
    if AI_RUNTIME_API_KEY:
        headers["Authorization"] = f"Bearer {AI_RUNTIME_API_KEY}"
    async with httpx.AsyncClient(
        base_url=AI_RUNTIME_BASE_URL,
        timeout=timeout,
        headers=headers,
    ) as client:
        application.state.runtime_client = client
        yield


app = FastAPI(
    title="KubeLaunch AI demo API",
    version="0.1.0",
    lifespan=lifespan,
)


def get_runtime_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.runtime_client


def build_runtime_request(prompt: str) -> tuple[str, dict[str, object]]:
    """Map the stable backend API to the selected runtime protocol."""
    if AI_RUNTIME == "ollama":
        return "/api/generate", {
            "model": AI_MODEL,
            "prompt": prompt,
            "stream": False,
        }
    return "/v1/chat/completions", {
        "model": AI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }


def extract_answer(payload: dict[str, object]) -> str:
    """Extract response text from Ollama or OpenAI-compatible vLLM JSON."""
    if AI_RUNTIME == "ollama":
        answer = payload.get("response")
    else:
        choices = payload.get("choices")
        answer = None
        if isinstance(choices, list) and choices:
            choice = choices[0]
            if isinstance(choice, dict):
                message = choice.get("message")
                if isinstance(message, dict):
                    answer = message.get("content")
    if not isinstance(answer, str) or not answer:
        raise ValueError(f"{AI_RUNTIME} response did not contain text")
    return answer


@app.get("/health")
async def health() -> dict[str, str]:
    """Report process health without invoking the model."""
    return {"status": "ok", "model": AI_MODEL, "runtime": AI_RUNTIME}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Expose Prometheus metrics on the application server."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/prompt", response_model=PromptResponse)
async def prompt(
    payload: PromptRequest,
    client: Annotated[httpx.AsyncClient, Depends(get_runtime_client)],
) -> PromptResponse:
    """Send one non-streaming prompt to the runtime and return its answer."""
    started_at = time.perf_counter()
    metric_status = "error"
    in_progress_metric = PROMPT_IN_PROGRESS.labels(**METRIC_LABELS)
    in_progress_metric.inc()
    try:
        path, runtime_payload = build_runtime_request(payload.prompt)
        response = await client.post(path, json=runtime_payload)
        response.raise_for_status()
        answer = extract_answer(response.json())
        metric_status = "success"
    except httpx.TimeoutException as error:
        raise HTTPException(status_code=504, detail="AI runtime timed out") from error
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(
            status_code=502,
            detail="AI runtime request failed",
        ) from error
    finally:
        elapsed_seconds = time.perf_counter() - started_at
        in_progress_metric.dec()
        PROMPT_REQUESTS.labels(status=metric_status, **METRIC_LABELS).inc()
        PROMPT_DURATION.labels(**METRIC_LABELS).observe(elapsed_seconds)

    return PromptResponse(
        answer=answer,
        model=AI_MODEL,
        response_time_ms=round(elapsed_seconds * 1000, 1),
    )
