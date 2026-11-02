# Proposal: Role assignment endpoints (user-role-assignment)

## Why

Today roles can only be set at account creation (`POST /users`, admin-only) or
by running `scripts/seed_users.py` on the server. There is no API to change an
existing user's roles, so a dispatcher cannot add the `driver` role to a driver
account without an admin, and the agreed role-authority matrix (who may grant
which role) is not enforceable. Jiří checked the live API docs and this gap is
visible there.

## What Changes

- New `PUT /api/v1/users/{user_id}/roles` - replaces a target user's role set
  in one idempotent write (full desired list; server computes grants and
  revokes). Revocation follows the same matrix as granting.
- Authority matrix enforced on every added AND every removed role:
  - `company-admin`, `system-admin`: only by `system-admin`
  - `dispatcher`: by `system-admin` or `company-admin`
  - `driver`: by `system-admin`, `company-admin` or `dispatcher`
- Dispatcher restrictions: a dispatcher (without admin roles) may only add or
  remove the `driver` role, only for users whose effective home group is one of
  the caller's groups (optionally set via `group_id` in the request), and never
  for users who already hold `dispatcher` or admin roles.
- Guards: nobody may change their own roles; no change may leave the system
  without an active `system-admin` (roles endpoint rejects demotion of the last
  holder as defense-in-depth; the reachable case - a lone system-admin
  deactivating their own account - is blocked with 409 on the deactivation
  endpoint); no partial change on rejection.
- Account creation and deactivation rules stay as they are (admins only, admin
  accounts reserved to system-admin).

Out of scope: dispatcher-web UI screens, changing the creation/deactivation
matrix, group-membership management (already in `organizational-groups`),
password changes, extending the seed script.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `identity-auth`: gains ADDED requirements "Role replacement endpoint",
  "Role assignment authority matrix", "Dispatcher driver-assignment scope" and
  "Role change escalation guards". Existing "User management by administrators"
  stays unchanged (creation/deactivation semantics are untouched).

## Impact

- `apps/api/app/routers/users.py` (new endpoint), `app/schemas/user.py`
  (request schema), new pure policy module (e.g. `app/role_policy.py`) shared
  with existing admin-account check in `users.py:19`.
- Idempotency middleware applies automatically (write endpoint) - no change.
- Tests: policy unit tests + router tests in `apps/api/tests/`.
- OpenAPI docs gain a `users`-tag operation; no DB migration (roles JSON
  column already exists).
