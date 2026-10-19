# System KAROLINA

IT system for a transport company – replaces the manual document-processing workflow
(today handled by an office administrator) with a dispatcher web portal and an
offline-first driver PWA: orders, transports, document collection and review.

📋 Background & business plan: [high-level-context.md](high-level-context.md) ·
[plan-system-karolina.md](plan-system-karolina.md) ·
**MVP1 plan (work in progress): [mvp1-implementation-plan.md](mvp1-implementation-plan.md)**

## Tech stack

| Layer    | Technology                                                        |
| -------- | ----------------------------------------------------------------- |
| Backend  | Python 3.13.7 (uv) · FastAPI · SQLAlchemy 2 (async) · Alembic      |
| Database | PostgreSQL 18                                                     |
| Storage  | Garage 2.4 (S3-compatible, presigned uploads)¹                    |
| Frontend | React + TypeScript + Vite (dispatcher portal + driver PWA)        |
| Infra    | Docker Compose · GitHub Actions CI · Caddy (planned, M8)          |

¹ MinIO was originally planned but is discontinued for self-hosting (repo archived 2026-04); see the rationale in the MVP1 plan.

## Repository layout

```
apps/api/             FastAPI backend (uv, health at /api/v1/health)
apps/dispatcher-web/  Dispatcher desktop portal (React + Vite)
apps/driver-pwa/      Offline-first driver PWA (React + Vite + vite-plugin-pwa)
packages/shared/      Shared types/utils (API client will be generated here)
infra/                docker-compose.yml + garage.toml
.github/workflows/    CI (backend lint/typecheck/tests, frontend lint/typecheck/build)
```

## Prerequisites

- [Docker](https://www.docker.com/) (for PostgreSQL + Garage)
- [uv](https://docs.astral.sh/uv/) (`brew install uv`) – Python 3.13.7 is resolved automatically from `apps/api/.python-version`
- [pnpm](https://pnpm.io/) 12+ and Node 22+

## Quick start

```bash
# 1. install dependencies
make api-install          # backend (uv sync)
pnpm install              # frontends

# 2. start infrastructure (postgres:5432, garage S3:9000)
make infra

# 3. run the apps (each in its own terminal)
make api-dev              # FastAPI on http://localhost:8000
make web                  # dispatcher portal on http://localhost:5173
make pwa                  # driver PWA on http://localhost:5174
```

Backend config lives in `apps/api/.env` (copy from `apps/api/.env.example` – defaults match the compose stack).

### Useful commands

```bash
make api-test             # pytest
make lint                 # ruff + oxlint
make typecheck            # mypy (strict) + tsc
make infra-down           # stop postgres + garage

# S3 round-trip smoke test (presigned PUT/GET against Garage)
cd apps/api && uv run python scripts/smoke_s3.py
```

API docs (debug mode): http://localhost:8000/api/docs

## Project status

**MVP1 – M0 complete** (monorepo scaffold, infra stack, CI).
Next: **M1 auth & users** → **M2 domain discovery** (the data model is intentionally
designed *after* discovery – see section 3 of the MVP1 plan).

## Ground rules

- All backend endpoints versioned under `/api/v1` – the OpenAPI spec is the contract for the future native iOS/Android app.
- Every write endpoint will require UUID primary keys + an `Idempotency-Key` (offline sync prerequisite).
- No POHODA / bank / OCR integration in MVP1 – only billing-ready data design (see MVP1 plan, section 2).
