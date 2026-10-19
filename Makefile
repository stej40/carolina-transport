.PHONY: help infra infra-down api-install api-dev api-test lint typecheck build

help:
	@echo "make infra        - start postgres + garage (s3)"
	@echo "make infra-down   - stop infra"
	@echo "make api-dev      - run FastAPI with reload"
	@echo "make api-test     - run backend tests"
	@echo "make web          - run dispatcher web dev server"
	@echo "make pwa          - run driver PWA dev server"
	@echo "make lint         - lint everything"
	@echo "make typecheck    - typecheck everything"

infra:
	docker compose -f infra/docker-compose.yml up -d postgres garage

infra-down:
	docker compose -f infra/docker-compose.yml down

api-install:
	cd apps/api && uv sync --all-groups

api-dev:
	cd apps/api && uv run uvicorn app.main:app --reload --port 8000

api-test:
	cd apps/api && uv run pytest

web:
	pnpm --filter dispatcher-web dev

pwa:
	pnpm --filter driver-pwa dev

lint:
	cd apps/api && uv run ruff check . && uv run ruff format --check .
	pnpm lint

typecheck:
	cd apps/api && uv run mypy app
	pnpm typecheck

build:
	pnpm build
