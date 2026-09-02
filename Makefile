# Convenience targets. `make help` lists them.

.DEFAULT_GOAL := help
.PHONY: help install install-backend install-frontend dev-backend dev-frontend \
        migrate revision test lint typecheck build rag-index models docker docker-down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install backend deps (dev + runtime)
	cd backend && pip install -r requirements-dev.txt

install-frontend: ## Install frontend deps
	cd frontend && npm ci

dev-backend: ## Run the API with autoreload on :8000
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend: ## Run the Next.js dev server on :3000
	cd frontend && npm run dev

migrate: ## Apply DB migrations (alembic upgrade head)
	cd backend && alembic upgrade head

revision: ## Autogenerate a migration: make revision m="add x"
	cd backend && alembic revision --autogenerate -m "$(m)"

models: ## (Re)train the ML models
	cd backend && python scripts/train_models.py

rag-index: ## (Re)build the RAG retrieval index
	cd backend && python scripts/build_rag_index.py

test: ## Run the backend test suite
	cd backend && pytest

lint: ## Lint backend (ruff) and frontend (eslint)
	cd backend && ruff check .
	cd frontend && npm run lint

typecheck: ## Typecheck the frontend
	cd frontend && npm run typecheck

build: ## Production build of the frontend
	cd frontend && npm run build

docker: ## Build and run the whole stack (db + api + web) with Docker Compose
	docker compose up --build

docker-down: ## Stop the stack and remove volumes
	docker compose down -v
