# Tasks: Idempotency for all write endpoints

## Middleware
- [x] 1.1 Invert scope in `app/idempotency.py`: all POST/PATCH/PUT/DELETE
  under `/api/v1` except `/api/v1/auth/*`; reject a scope-covered write without
  an `Idempotency-Key` header with 400 (clear detail message); verify new
  endpoint test shows 400 then success with a key
- [x] 1.2 Handle non-JSON success bodies (204/empty): store
  `{"status": code, "body": null}` so later replays answer with the stored
  empty response instead of 409 "in flight"; verify with a replay of
  `PUT /groups/{id}/members/{uid}`
- [x] 1.3 Startup retention: on app startup delete `idempotency_keys` rows
  older than 30 days; verify with a seeded old row removed and a fresh row
  kept

## Test migration
- [x] 2.1 Add an `Idempotency-Key` header (unique per call) to all existing
  write requests in `tests/test_auth.py`, `tests/test_user_admin.py`,
  `tests/test_organizational_groups.py`, `tests/test_transport_lifecycle.py`
  where required (all except `/auth/*`); full `make api-test` green
- [x] 2.2 New tests in `tests/test_idempotency.py`: replay on a non-domain
  endpoint (`POST /users`) returns original 201 with
  `Idempotency-Replayed: true` and no duplicate; missing key on `POST /users`
  and `DELETE /users/{id}/deactivate` -> 400; auth exemption: two logins
  succeed without key and produce no `idempotency_keys` rows; conflicting
  reuse -> 422 kept from current suite

## Gate
- [x] 3.1 `make lint && make typecheck && make api-test` green; `alembic
  check` still empty (no schema change)
