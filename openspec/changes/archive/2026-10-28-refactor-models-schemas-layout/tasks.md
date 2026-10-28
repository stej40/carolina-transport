# Tasks: Refactor API models & schemas layout

## 1. Models package
- [x] 1.1 Create `app/models/` package: `common.py` (`utcnow`, `ROLES`,
  `ADMIN_ROLES`, `LANGUAGES`), `user.py` (User, RefreshToken), `group.py`
  (Group, GroupMember), `fleet.py` (FleetMixin, Truck, Trailer) - verbatim
  class bodies, no field changes; verify `python -c "import app.models"`
  resolves all mappers
- [x] 1.2 Write `app/models/__init__.py` re-exporting every public name with
  `__all__` in dependency order (common, user, group, fleet); delete
  `app/models.py`; verify `from app.models import User, Truck, ROLES` works
- [x] 1.3 Verify Alembic sees identical metadata: autogenerate a revision
  against the dev DB and confirm the diff is empty (revision file contains
  no operations, then discard it)

## 2. Schemas package
- [x] 2.1 Create `app/schemas/` package: `common.py` (`Language`, `Role`),
  `auth.py`, `user.py`, `group.py`, `fleet.py` per design.md grouping -
  verbatim class bodies; `__init__.py` re-exports all; delete
  `app/schemas.py`; verify `from app.schemas import GroupDetailOut` works
- [x] 2.2 Confirm OpenAPI is unchanged: dump `/api/v1/openapi.json` before
  and after the move (or run the app and diff) and verify no difference

## 3. Convention & green build
- [x] 3.1 Add the layout rule ("one module per entity under
  `apps/api/app/models/` and `apps/api/app/schemas/`, aggregation only via
  `__init__.py` re-exports") to `AGENTS.md` (Stack & layout) and to the
  Conventions block in `openspec/config.yaml`
- [x] 3.2 Full gate: `make lint && make typecheck && make api-test` green;
  routers, `deps.py`, `migrations/env.py`, tests and `scripts/seed_users.py`
  contain no import edits (grep confirms they still use `app.models` /
  `app.schemas`)
