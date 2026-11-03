# Design

## Context

See proposal.md - Why. Current state: the API's only account-creation paths are
admin-gated (`users.py` requires a system-admin to create admins) plus the
manual CLI `scripts/seed_users.py`. `users.py` already guards "cannot leave the
system without an active system-admin" (409), but the CLI seed script can
overwrite roles wholesale, so a DB can still end up with zero active
system-admins; the startup guard must cover that. `Settings` uses profile
dotenv files with an existing prod fail-fast validator
(`_prod_safety`, config.py:46) and a placeholder-rejection pattern for
`SECRET_KEY`. `User.email` is unique (lower-cased by all writers), roles are a
JSON list, `is_active` exists. Lifespan (main.py:27) already runs
`purge_stale_idempotency_keys` before `yield`. Tests drive the app through
httpx `ASGITransport`, which does NOT execute lifespan, so the bootstrap
routine must be callable (and testable) independently of app startup.

## Goals / Non-Goals

**Goals:**
- Fresh or locked-out databases are self-healing on the next start; a pilot
  deployment needs zero manual seeding.
- One deterministic admin identity (`BOOTSTRAP_ADMIN_EMAIL`) with
  profile-appropriate credentials; prod refuses to run on dev credentials.
- The guard is a no-op whenever the invariant already holds - safe to run on
  every start, every replica.

**Non-Goals:**
- Continuous enforcement between restarts (no timers, no middleware checks).
- First-login password change, expiry/rotation, 2FA.
- Changing `seed_users.py` or the user-admin endpoints.
- Encrypting or externalising the bootstrap password beyond the existing
  dotenv mechanism (`.env.*` files stay git-ignored per the runtime-config
  spec).

## Decisions

1. **New module `app/bootstrap.py`** with
   `async def ensure_system_admin(session_maker) -> BootstrapResult`
   (returns what happened for logging/tests), called from `lifespan` right
   after the idempotency purge. Alternative: Alembic data migration -
   rejected: seeds would fire on every environment running migrations
   (including CI/test DBs) and prod values live in dotenv, not migrations; a
   lifespan hook matches the existing `purge_stale_idempotency_keys` pattern.
2. **Invariant check**: `SELECT 1 FROM users WHERE is_active AND 'system-admin' = ANY/MAP roles`
   - roles are a JSON list, so the check loads candidate emails in SQL and
     filters role membership in Python for correctness across Postgres and
     SQLite (test DB). Cheap: only rows with `is_active` are inspected;
     deployment size is tens of users. If any exists -> no-op.
3. **Revive-or-create**: when the invariant is violated, look up
   `BOOTSTRAP_ADMIN_EMAIL.lower()`. If the row exists: set `is_active=True`,
   add `system-admin` to its roles (other roles kept), and reset
   `password_hash` to the configured password (documented in the spec - the
   hash is one-way; reviving without a password reset would not restore
   usability). If no row exists: create the user (active, roles
   `["system-admin"]`). Race between replicas resolves on the unique-email
   index: catch `IntegrityError`, roll back, treat as success.
4. **Settings** (config.py):
   `bootstrap_admin_email: str = "systemadmin@example.local"`,
   `bootstrap_admin_password: str = DEV_BOOTSTRAP_PASSWORD_PLACEHOLDER`
   (`"dev-bootstrap-password-change-me"`, module constant mirroring
   `DEV_SECRET_PLACEHOLDER`). Extend `_prod_safety`: in prod the bootstrap
   password must not equal the placeholder and must be >=
   `PROD_MIN_PASSWORD_LEN = 12`; email must be non-empty. Rationale for a
   length floor of 12: admin password, human-typed, consistent with the
   existing "unique and long enough" style for SECRET_KEY (32) while not
   blocking operators who choose a passphrase. Alternatives: random
   generated password logged once - rejected by Jiří in favour of
   env-configurable credentials; separate `bootstrap` CLI - rejected: keeps
   the "usable from the beginning" guarantee automatic.
5. **Logging**: one INFO line (`bootstrap admin created|revived|not needed`),
   never the password; no e-mail/notification.
6. **Testability**: unit-test `ensure_system_admin` directly against the
   SQLite fixture session (fresh DB, locked-out DB, healthy DB, revive keeps
   other roles); extend `test_runtime_configuration.py` with the prod
   placeholder/short-password rejections and the local default acceptance.
   Lifespan wiring is asserted by a small test calling `main.lifespan`
   context or by relying on the direct function tests (chosen: direct tests -
   lifespan execution under ASGITransport is out of scope).

## Risks / Trade-offs

- [Revive resets the bootstrap password on every lock-out restart] → intended
  and spec'd; the only active-admin path is by definition unusable otherwise.
  Mitigation: operators should create named admin accounts; the bootstrap
  account is the emergency floor.
- [Dev placeholder usable in a mislabelled prod (APP_ENV not prod)] → same
  exposure as SECRET_KEY placeholder today; deployment must set APP_ENV=prod.
- [Role filter in Python loads all active users at startup] → negligible at
  this company's scale; revisit only if user count grows.
- [Startup now writes users] → idempotent, single row, no schema change;
  failure (DB unreachable) already prevents serving via existing startup.
