# Backend

FastAPI-backenden tar imot en prompt på `POST /api/prompt`, sender den videre
til `tinyllama` i Ollama og returnerer svaret med målt responstid.

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
