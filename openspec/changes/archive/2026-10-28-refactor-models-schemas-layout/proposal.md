# Proposal: Refactor API models & schemas layout

## Why
All SQLAlchemy models live in one `app/models.py` and all Pydantic schemas in
one `app/schemas.py`. The pending `mvp1-transports-and-orders` change alone
adds ~7 more entities (orders, transports, transport_events, transport_drivers,
portal_settings, external_ids, idempotency_keys), and MVP2-MVP4 add more. A
single-file layout will not scale - split it now, before new domain code lands,
so per-entity files are born here instead of migrated out later.

## What Changes
- Convert `app/models.py` into a package `app/models/`: one module per entity
  (or cohesive entity family), plus `common.py` for shared pieces (`utcnow`,
  role/language constants) and an `__init__.py` that re-exports every name.
- Convert `app/schemas.py` into a package `app/schemas/`: one module per
  entity family (auth, user, group, fleet) with the same re-export pattern.
- No behavior, no API contract, no schema/DB change: existing imports
  (`from app.models import User`, `from app.schemas import ...`) keep working
  unchanged via package re-exports - routers, deps, Alembic env, tests and
  seed scripts are not touched.
- Record the layout convention in `AGENTS.md` and the `openspec/config.yaml`
  context so all future changes follow it.

No spec-level behavior changes - this change sets `skip_specs: true`.

## Out of scope
New entities (they come with mvp1-transports-and-orders), router or service
layer restructuring, moving `db.py`/`deps.py`/`security.py`, any change to
OpenAPI output, tests or endpoints.

## Capabilities
### New Capabilities
(none - pure internal refactor, `skip_specs: true`)

### Modified Capabilities
(none - no requirement changes)

## Impact
- `apps/api/app/`: `models.py` -> `models/` package, `schemas.py` ->
  `schemas/` package; all other files unchanged.
- Alembic autogenerate must produce an empty diff afterwards (metadata
  identical); `make lint && make typecheck && make api-test` must stay green.
- No `packages/shared` regeneration needed (OpenAPI unchanged).
