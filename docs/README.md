# Dokumentasjon

Her kommer det etter hvert mer detaljer om arkitektur, demo-oppsett og planen
for skjermbilder eller GIF. Den overordnede arkitekturen står foreløpig i
[hoved-README-en](../README.md#arkitektur).

## Videre plan

Prosjektet bygges i små deler som kan testes og committes hver for seg:

0. Grunnstruktur for repoet
1. CLI-grunnlag og sjekk av nødvendige verktøy
2. Opprette og slette lokalt k3d-cluster
3. Installere Argo CD
4. Verifisere app-of-apps
5. Legge til Prometheus og Grafana
6. Installere KEDA og teste enkel skalering
7. Kjøre Ollama som en stabil workload
8. Lage FastAPI-backend for AI-demoen
9. Lage frontend for AI-demoen (fullført)
10. Skalere backend med KEDA (fullført)
11. Gjøre CLI-et ferdig og mer oversiktlig
12. Pusse opp dokumentasjon, demo og CI

Etter MVP-en kan prosjektet utvides med blant annet `--full`-modus,
cert-manager, External Secrets, en `AIWorkload`-operator, vLLM, canary-utrulling
og guider for kjøring i skyen.
