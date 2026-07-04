.DEFAULT_GOAL := help

.PHONY: help setup up status down test lint validate

help: ## Show available development tasks
	@echo "KubeLaunch development tasks"
	@echo ""
	@echo "  make setup      Install the CLI and development dependencies"
	@echo "  make up         Validate the host for the minimal platform"
	@echo "  make status     Show local platform status"
	@echo "  make down       Run the platform cleanup command"
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

test:
	python -m pytest

lint:
	python -m ruff check .

validate:
	python -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('platform/root-application.yaml').read_text(encoding='utf-8')); print('Platform YAML is valid.')"
