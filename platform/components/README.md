# Plattformkomponenter

Hver YAML-fil her beskriver én child Application som Argo CD skal håndtere.
Smoke-testen verifiserer GitOps-flyten. `observability-application.yaml`
installerer Prometheus og Grafana fra et pinna Helm-chart. KEDA installeres av
`keda-application.yaml`, mens `keda-smoke-test-application.yaml` tester
autoskalering isolert. `ollama-application.yaml` kjører én persistent AI-runtime.
AI-demoen legges til i egne milepæler.
