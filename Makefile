.DEFAULT_GOAL := help

.PHONY: help setup up status down grafana test lint validate

help: ## Show available development tasks
	@echo "KubeLaunch development tasks"
	@echo ""
	@echo "  make setup      Install the CLI and development dependencies"
	@echo "  make up         Validate the host for the minimal platform"
	@echo "  make status     Show local platform status"
	@echo "  make down       Run the platform cleanup command"
	@echo "  make grafana    Forward Grafana to http://localhost:3000"
	@echo "  make test       Run available tests"
	@echo "  make lint       Run available linters"
	@echo "  make validate   Validate platform definitions"

setup:
	python -m pip install -e ".[dev]"

up:
	kube-launch up --minimal

status:
	kube-launch status

down:
	kube-launch down

grafana:
	kubectl --context k3d-kubelaunch --namespace monitoring port-forward service/kubelaunch-grafana 3000:80

test:
	python -m pytest

lint:
	python -m ruff check .

validate:
	python scripts/validate_manifests.py
	kubectl kustomize apps/platform-smoke-test
