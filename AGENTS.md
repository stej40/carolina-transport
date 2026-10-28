# AGENTS.md - Project rules (System KAROLINA / agro-karolina)

## Documentation & planning - OpenSpec is mandatory
- All planning and specification lives in `openspec/` (managed by the
  OpenSpec CLI). `docs/planning-archive/` is historical only - never add new
  docs there.
- Every new MVP, feature, or behavioral change MUST start as an OpenSpec
  change: `/opsx-propose <name>` (or `openspec new change <name>`) with
  proposal.md, spec deltas, design.md, and tasks.md - approved by Jiří before
  implementation. No domain code without an approved change.
- Completed changes are archived with `/opsx-archive`, which folds spec
  deltas into `openspec/specs/`.
- After upgrading the OpenSpec CLI, run `openspec update` in this repo.

## Language
- All artifacts, code comments, commits, and docs are written in English.
  Czech domain terms (objednavka, vazni listek, preprava) may be cited in
  specs.

## Stack & layout (locked decisions)
- Monorepo: `apps/api` (Python 3.13.7, FastAPI, uv), `apps/dispatcher-web`
  and `apps/driver-pwa` (React + TS + Vite, pnpm workspaces),
  `packages/shared` (generated API types), `infra/` (Docker Compose:
  postgres:18-alpine, Garage 2.4 S3).
- Backend: SQLAlchemy 2.x async + asyncpg, Alembic migrations only, Pydantic
  v2. API is versioned under `/api/v1`; OpenAPI spec is the contract.
- API layout: one module per entity under `apps/api/app/models/` and
  `apps/api/app/schemas/`; aggregation only via `__init__.py` re-exports
  (consumers keep importing `app.models` / `app.schemas`).
- Auth: own JWT module (access + refresh), RBAC roles `dispatcher`/`driver`,
  argon2 hashing.
- Do not introduce new infrastructure components (e.g., MinIO, Redis,
  message queues) without an approved OpenSpec change that justifies them.

## Data-model invariants (cheap now, expensive later)
- UUID primary keys, client-generatable (offline creation).
- Idempotency keys on all write endpoints (offline outbox replays).
- Money as NUMERIC, never float; one agreed rounding policy.
- Transport state transitions stored in an immutable append-only event log.
- Orders stay billing-ready (quantity, unit, unit price, currency, VAT,
  billing text); invoices will carry a system-owned variable symbol (VS).
- External-ID mapping table for later POHODA sync; document types are data,
  not enums.

## Working rules
- Use `make` targets: `make infra`, `make api-dev`, `make api-test`,
  `make lint`, `make typecheck`, `make web`, `make pwa`.
- Run `make lint && make typecheck` and backend tests (`make api-test`)
  before declaring work done.
- M2 domain discovery is a hard gate: no domain schema migration until the
  schema proposal is signed off by Jiří.
