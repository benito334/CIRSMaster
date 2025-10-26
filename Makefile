SHELL := /bin/bash
.DEFAULT_GOAL := help

VERSION ?= $(shell cat VERSION 2>/dev/null || echo dev)

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

up: ## Start dev stack
	docker compose up -d

stop: ## Stop dev stack
	docker compose down

build: ## Build all images locally
	docker compose build --parallel

lint: ## Run linters
	python -m pip install -q ruff bandit || true
	ruff check . || true
	bandit -q -r backend || true
	cd frontend/chat_ui && npm ci && npm run lint --if-present || true

test: ## Run unit tests
	python -m pip install -q pytest || true
	pytest -q || true

sbom: ## Create SBOMs into ./sbom/
	./scripts/sbom.sh

deploy: ## Deploy local prod stack
	./scripts/deploy_local.sh

migrate: ## Run DB migrations
	./scripts/migrate.sh
