.DEFAULT_GOAL := help

.PHONY: help setup up status down grafana keda-load keda-status ollama backend-image backend test lint validate

help: ## Show available development tasks
	@echo "KubeLaunch development tasks"
	@echo ""
	@echo "  make setup      Install the CLI and development dependencies"
	@echo "  make up         Validate the host for the minimal platform"
	@echo "  make status     Show local platform status"
	@echo "  make down       Run the platform cleanup command"
	@echo "  make grafana    Forward Grafana to http://localhost:3000"
	@echo "  make keda-load  Generate CPU load for the KEDA smoke test"
	@echo "  make keda-status Show KEDA scaling resources"
	@echo "  make ollama     Forward Ollama to http://localhost:11434"
	@echo "  make backend-image Build and import the backend image into k3d"
	@echo "  make backend    Forward the backend to http://localhost:8000"
	@echo "  make test       Run available tests"
	@echo "  make lint       Run available linters"
	@echo "  make validate   Validate platform definitions"

setup:
	python -m pip install -e ".[backend,dev]"

up:
	kube-launch up --minimal

status:
	kube-launch status

down:
	kube-launch down

grafana:
	kubectl --context k3d-kubelaunch --namespace monitoring port-forward service/kubelaunch-grafana 3000:80

keda-load:
	kubectl --context k3d-kubelaunch --namespace kubelaunch-system run keda-load --image=busybox:1.36 --restart=Never --rm -it -- /bin/sh -c "while true; do wget -q -O- http://keda-smoke-test; done"

keda-status:
	kubectl --context k3d-kubelaunch --namespace kubelaunch-system get scaledobject,hpa,deployment

ollama:
	kubectl --context k3d-kubelaunch --namespace ollama port-forward service/ollama 11434:11434

backend-image:
	docker build --tag kubelaunch-backend:dev apps/ai-demo/backend
	k3d image import kubelaunch-backend:dev --cluster kubelaunch

backend:
	kubectl --context k3d-kubelaunch --namespace ai-demo port-forward service/ai-demo-backend 8000:8000

test:
	python -m pytest

lint:
	python -m ruff check .

validate:
	python scripts/validate_manifests.py
	kubectl kustomize apps/platform-smoke-test
	kubectl kustomize apps/keda-smoke-test
	kubectl kustomize apps/ollama
	kubectl kustomize apps/ai-demo/backend/k8s
