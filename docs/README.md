# KubeLaunch documentation

This directory will collect detailed architecture notes, demo instructions,
and a screenshot/GIF plan as the project becomes runnable. The high-level
architecture currently lives in the repository root README.

## Roadmap

The MVP will be delivered incrementally:

0. Repository scaffolding and project foundation
1. CLI skeleton and prerequisite checks
2. Idempotent k3d cluster lifecycle
3. Argo CD bootstrap
4. App-of-apps validation
5. Prometheus and Grafana
6. KEDA installation and isolated scaling test
7. Ollama runtime
8. FastAPI AI demo backend
9. AI demo frontend
10. KEDA autoscaling for the backend
11. CLI polish
12. Documentation, demo assets, and CI

Post-MVP candidates include a `--full` mode with cert-manager and External
Secrets, an `AIWorkload` CRD/controller, vLLM, canary model rollout, custom AI
dashboards, and cloud deployment guides.
