# Dokumentasjon

Den overordnede arkitekturen, demo-oppsettet og kommandoene for lokal kjøring
står i [hoved-README-en](../README.md). Plattformen valideres automatisk av
GitHub Actions og kan demonstreres lokalt gjennom frontenden.

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
11. Gjøre CLI-et ferdig og mer oversiktlig (fullført)
12. Pusse opp dokumentasjon, demo og CI (fullført)

Etter MVP-en er `--full`-modus, cert-manager og en lokal External Secrets/Vault-
demo og en `AIWorkload`-operator lagt til. Operator-workloads kan nå bruke både
Ollama og et OpenAI-kompatibelt vLLM-endepunkt, samt kjøre replica-basert canary
med en separat Deployment. Et eksisterende Kubernetes-cluster kan nå bootstrappes
med eksplisitt context, Git-kilde og registry-images; se
[sky-cluster-guiden](cloud.md). Canary-operatoren analyserer Deployment-readiness
periodisk og lager en Prometheus-alert for konfigurerbar canary-feilrate uten å
auto-promotere. Prosjektet kan videre utvides med modellkvalitet/evaluering,
DNS-automatisering og leverandørspesifikk infrastrukturkode.
