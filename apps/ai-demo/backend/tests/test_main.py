import asyncio
from collections.abc import AsyncIterator

import httpx
from app import main
from app.main import app, get_runtime_client


async def request(
    method: str,
    path: str,
    *,
    json: dict[str, str] | None = None,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        base_url="http://backend.test",
        transport=transport,
    ) as client:
        return await client.request(method, path, json=json)


async def prompt_request(
    runtime_transport: httpx.MockTransport,
    prompt: str,
) -> httpx.Response:
    async def override_client() -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient(
            base_url="http://runtime.test",
            transport=runtime_transport,
        ) as client:
            yield client

    app.dependency_overrides[get_runtime_client] = override_client
    try:
        return await request("POST", "/api/prompt", json={"prompt": prompt})
    finally:
        app.dependency_overrides.clear()


def test_health_reports_model() -> None:
    response = asyncio.run(request("GET", "/health"))

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "model": "tinyllama",
        "runtime": "ollama",
    }


def test_prompt_returns_ollama_answer() -> None:
    captured_request: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        captured_request["body"] = request.content
        return httpx.Response(200, json={"response": "Et kort svar."})

    response = asyncio.run(prompt_request(httpx.MockTransport(handler), "Hei Ollama"))

    assert response.status_code == 200
    assert response.json()["answer"] == "Et kort svar."
    assert response.json()["model"] == "tinyllama"
    assert response.json()["response_time_ms"] >= 0
    assert captured_request["url"] == "http://runtime.test/api/generate"
    assert b'"stream":false' in captured_request["body"]


def test_prompt_rejects_blank_text() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("Ollama must not be called for an invalid prompt")

    response = asyncio.run(prompt_request(httpx.MockTransport(handler), "   "))

    assert response.status_code == 422


def test_prompt_maps_ollama_failure_to_bad_gateway() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "model failed"})

    response = asyncio.run(prompt_request(httpx.MockTransport(handler), "Hei"))

    assert response.status_code == 502
    assert response.json() == {"detail": "AI runtime request failed"}


def test_prompt_maps_vllm_openai_compatible_response(monkeypatch) -> None:
    captured_request: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        captured_request["body"] = request.content
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Svar fra vLLM."}}]},
        )

    monkeypatch.setattr(main, "AI_RUNTIME", "vllm")
    monkeypatch.setattr(main, "AI_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
    response = asyncio.run(
        prompt_request(httpx.MockTransport(handler), "Hei vLLM")
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Svar fra vLLM."
    assert response.json()["model"] == "Qwen/Qwen2.5-0.5B-Instruct"
    assert captured_request["url"] == "http://runtime.test/v1/chat/completions"
    assert b'"role":"user"' in captured_request["body"]
    assert b'"content":"Hei vLLM"' in captured_request["body"]


def test_metrics_expose_prompt_counter() -> None:
    response = asyncio.run(request("GET", "/metrics"))

    assert response.status_code == 200
    assert "kubelaunch_prompt_requests_total" in response.text
    assert "kubelaunch_prompt_duration_seconds" in response.text
    assert "kubelaunch_prompt_requests_in_progress" in response.text
    assert 'model="tinyllama"' in response.text
    assert 'runtime="ollama"' in response.text
    assert 'track="stable"' in response.text
