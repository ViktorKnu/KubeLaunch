.DEFAULT_GOAL := help

.PHONY: help setup up status down test lint validate

help: ## Show available development tasks
	@echo "KubeLaunch development tasks"
	@echo ""
	@echo "  make setup      Prepare the local development environment (planned)"
	@echo "  make up         Start the minimal local platform (planned)"
	@echo "  make status     Show local platform status (planned)"
	@echo "  make down       Remove the local platform (planned)"
	@echo "  make test       Run available tests"
	@echo "  make lint       Run available linters"
	@echo "  make validate   Validate platform definitions"

setup up status down:
	@echo "$@ is not implemented yet; see the milestone plan in docs/README.md."

test:
	@echo "No tests are defined yet."

lint:
	@echo "No linters are configured yet."

validate:
	@echo "No platform definitions are available to validate yet."
