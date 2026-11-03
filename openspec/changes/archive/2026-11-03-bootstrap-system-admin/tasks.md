# Tasks

## 1. Configuration

- [x] 1.1 Add `bootstrap_admin_email` (default `systemadmin@example.local`) and `bootstrap_admin_password` (module constant `DEV_BOOTSTRAP_PASSWORD = "dev-bootstrap-password-change-me"`) to `Settings` in `apps/api/app/config.py`; extend `_prod_safety` to reject, in the prod profile, an empty/placeholder bootstrap password, one shorter than `PROD_MIN_PASSWORD_LEN = 12`, and an empty email. Verify with `uv run python -c "from app.config import Settings"` style probes plus the tests in 3.2.
- [x] 1.2 Document the two variables (with the dev placeholder note) in `apps/api/.env.example` and `apps/api/.env.local` header comments, matching the existing comment style.

## 2. Bootstrap routine and startup wiring

- [x] 2.1 Create `apps/api/app/bootstrap.py`: `async def ensure_system_admin(session_maker) -> str` implementing design decisions 2-3 and 5 (invariant = any active user whose roles JSON contains `system-admin`, filtered in Python across Postgres/SQLite; revive-or-create by lower-cased `bootstrap_admin_email` with password-hash reset on revive; `IntegrityError` -> rollback + "created concurrently" result; INFO log line that never contains the password; no module-level import of FastAPI).
- [x] 2.2 Call `ensure_system_admin(app.state.session_maker)` from the `lifespan` hook in `apps/api/app/main.py` immediately after `purge_stale_idempotency_keys`.

## 3. Tests

- [x] 3.1 New `apps/api/tests/test_bootstrap_admin.py` against the SQLite `session_maker` fixture: fresh DB creates the account (active, `system-admin`, configurable email, sign-in works via `/api/v1/auth/login` with the configured password); healthy DB (active admin exists, bootstrap row disabled/demoted) changes nothing; lock-out DB (only admin disabled via direct row edit) revives the row, keeps non-admin roles, resets the password (old hash stops working, configured password logs in); running twice is a no-op. Assert no password appears in captured log records.
- [x] 3.2 Extend `apps/api/tests/test_runtime_configuration.py`: prod rejects placeholder password, empty password and a 5-char password; prod accepts a compliant password; local accepts defaults. Follow the existing tmp_path env-file test style.

## 4. Verification

- [x] 4.1 `make lint && make typecheck && make api-test` all green.
- [x] 4.2 Dev-stack check: with an empty fresh Postgres schema or after demoting all admins (`docker exec ... psql` role edit), `make infra-full` + restart -> `curl` login as the bootstrap admin returns 200; a second restart logs "not needed" and changes nothing.
