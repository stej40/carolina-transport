# Design: Refactor API models & schemas layout

## Context
See proposal.md - Why. Current state: `app/models.py` holds `Base` subclasses
for User, RefreshToken, Group, GroupMember, FleetMixin/Truck/Trailer plus
`utcnow()` and role/language constants; `app/schemas.py` holds Pydantic
schemas for auth, users, groups, fleet plus `Language`/`Role` literals.
Consumers import via `from app.models import X` / `from app.schemas import X`
(routers, `deps.py`, `migrations/env.py`, tests, `scripts/seed_users.py`).

## Goals / Non-Goals

**Goals:**
- One module per entity (or cohesive family) under `app/models/` and
  `app/schemas/`, scalable to MVP1-MVP4 entity growth.
- Zero import churn: every existing `from app.models import ...` /
  `from app.schemas import ...` line keeps working.
- SQLAlchemy metadata and OpenAPI output byte-identical after the move.

**Non-Goals:**
- Splitting routers into services, renaming modules, changing `db.py`.
- Any new entities or fields (domain code stays as-is).

## Decisions
- **Module -> package with re-export `__init__.py`.** `app/models.py` is
  replaced by `app/models/__init__.py` re-exporting all public names, so
  consumers need no edits and Alembic's `import app.models` still registers
  all tables (each entity module imports `Base` from `app.db`; the package
  `__init__` imports every module, guaranteeing full mapper registration).
  Alternative considered: update all imports to submodule paths - rejected,
  it touches 10+ files for no behavioral gain and invites drift.
- **Grouping granularity.** `models/`: `common.py` (`utcnow`, `ROLES`,
  `ADMIN_ROLES`, `LANGUAGES`), `user.py` (User, RefreshToken - RefreshToken
  is an auth artifact of the user aggregate), `group.py` (Group,
  GroupMember), `fleet.py` (FleetMixin, Truck, Trailer). `schemas/`:
  `common.py` (`Language`, `Role` literals), `auth.py` (LoginRequest,
  TokenPair, RefreshRequest), `user.py` (UserOut, UserCreate, ProfileUpdate),
  `group.py` (GroupCreate/Update/Out/DetailOut, GroupMove), `fleet.py`
  (FleetCreate, FleetOut). One class per file was rejected for tight couples
  (Truck/Trailer share FleetMixin; GroupDetailOut embeds UserOut/FleetOut);
  future domain entities (Order, Transport, ...) each get their own file.
- **Circular-import guard.** Current models use plain FK columns (no
  `relationship()`), so cross-module references are not needed; if a future
  relationship is added, reference the target by string class name and import
  it only under `TYPE_CHECKING`. `__init__.py` imports submodules in
  dependency order (common, user, group, fleet).
- **Convention becomes a rule, not a comment.** The layout rule is recorded
  in `AGENTS.md` (Working rules/Stack & layout) and `openspec/config.yaml`
  context so every future proposal's tasks implicitly follow it; a code
  comment in each `__init__.py` points to the rule.

## Risks / Trade-offs
- [Re-export hides accidental dead imports] → lint (`make lint`) runs in CI
  on the package; `__init__.py` is the only allowed aggregation point.
- [Alembic autogenerate noise if a model file is forgotten] → acceptance
  check: autogenerate after refactor must produce an empty migration diff.
- [Tests import private helpers from `models.py` in the future] → tests use
  public names; the package `__all__` lists them.

## Migration Plan
Pure code move in one commit; rollback = revert commit. No data, no deploy
steps beyond normal API redeploy.
