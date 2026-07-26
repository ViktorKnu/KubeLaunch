# Backend

FastAPI-backenden tar imot en prompt på `POST /api/prompt`, sender den videre
til valgt AI-runtime og returnerer svaret med målt responstid. `ollama` bruker
`/api/generate`, mens `vllm` bruker det OpenAI-kompatible
`/v1/chat/completions`-endepunktet.

Runtime konfigureres med `AI_RUNTIME`, `AI_RUNTIME_BASE_URL`, `AI_MODEL` og
`AI_TIMEOUT_SECONDS`. `AI_RUNTIME_API_KEY` kan settes når det kompatible
endepunktet krever Bearer-autentisering. De gamle `OLLAMA_*`-variablene støttes
fortsatt som fallback.

KEDA skalerer backenden mellom én og tre replikaer basert på Prometheus-metrikken
`kubelaunch_prompt_requests_in_progress`. Hver replika sikter mot maksimalt én
aktiv prompt om gangen. Ollama skaleres ikke.

Endepunkter:

- `GET /health` – enkel prosessjekk
- `GET /metrics` – Prometheus-metrics
- `POST /api/prompt` – prompt inn, modellsvar ut

Kjør tester fra roten av repoet med `python -m pytest`. Se
[hoved-README-en](../../../README.md#test-backenden) for lokal bygging og test
mot clusteret.
