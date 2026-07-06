# Plattformkomponenter

Hver YAML-fil her beskriver én child Application som Argo CD skal håndtere.
Smoke-testen verifiserer GitOps-flyten. `observability-application.yaml`
installerer Prometheus og Grafana fra et pinna Helm-chart. KEDA, Ollama og
AI-demoen legges til i egne milepæler.
