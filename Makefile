.DEFAULT_GOAL := help

.PHONY: help setup up full status down grafana keda-load keda-status backend-scale-status cert-status ollama backend-image backend frontend-image frontend test lint validate

help: ## Show available development tasks
	@echo "KubeLaunch development tasks"
	@echo ""
	@echo "  make setup      Install the CLI and development dependencies"
	@echo "  make up         Validate the host for the minimal platform"
	@echo "  make full       Bootstrap the extended platform with cert-manager"
	@echo "  make status     Show local platform status"
	@echo "  make down       Run the platform cleanup command"
	@echo "  make grafana    Forward Grafana to http://localhost:3000"
	@echo "  make keda-load  Generate CPU load for the KEDA smoke test"
	@echo "  make keda-status Show KEDA scaling resources"
	@echo "  make backend-scale-status Show backend KEDA scaling resources"
	@echo "  make cert-status Show cert-manager certificate resources"
	@echo "  make ollama     Forward Ollama to http://localhost:11434"
	@echo "  make backend-image Build and import the backend image into k3d"
	@echo "  make backend    Forward the backend to http://localhost:8000"
	@echo "  make frontend-image Build and import the frontend image into k3d"
	@echo "  make frontend   Forward the frontend to http://localhost:8080"
	@echo "  make test       Run available tests"
	@echo "  make lint       Run available linters"
	@echo "  make validate   Validate platform definitions"

setup:
	python -m pip install -e ".[backend,dev]"

up:
	kube-launch up --minimal

full:
	kube-launch up --full

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

backend-scale-status:
	kubectl --context k3d-kubelaunch --namespace ai-demo get scaledobject,hpa,deployment

cert-status:
	kubectl --context k3d-kubelaunch --namespace kubelaunch-system get certificate,secret

ollama:
	kubectl --context k3d-kubelaunch --namespace ollama port-forward service/ollama 11434:11434

backend-image:
	docker build --tag kubelaunch-backend:dev apps/ai-demo/backend
	k3d image import kubelaunch-backend:dev --cluster kubelaunch

backend:
	kubectl --context k3d-kubelaunch --namespace ai-demo port-forward service/ai-demo-backend 8000:8000

frontend-image:
	docker build --tag kubelaunch-frontend:dev apps/ai-demo/frontend
	k3d image import kubelaunch-frontend:dev --cluster kubelaunch

frontend:
	kubectl --context k3d-kubelaunch --namespace ai-demo port-forward service/ai-demo-frontend 8080:8080

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
	kubectl kustomize apps/ai-demo/frontend/k8s
	kubectl kustomize apps/cert-manager-smoke-test
