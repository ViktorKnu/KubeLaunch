# Backend

FastAPI-backenden tar imot en prompt på `POST /api/prompt`, sender den videre
til `tinyllama` i Ollama og returnerer svaret med målt responstid.

Endepunkter:

- `GET /health` – enkel prosessjekk
- `GET /metrics` – Prometheus-metrics
- `POST /api/prompt` – prompt inn, modellsvar ut

Kjør tester fra roten av repoet med `python -m pytest`. Se
[hoved-README-en](../../../README.md#test-backenden) for lokal bygging og test
mot clusteret.
