# Tasks

## 1. Role policy module

- [x] 1.1 Create `apps/api/app/role_policy.py` with the authority-table constant, `evaluate_role_change(...)` returning reason-code lists (self-change, authority, dispatcher-scope, last-system-admin) and dataclass-style inputs per design decisions 1-4; verify with table-driven unit tests in `apps/api/tests/test_role_policy.py` covering the full matrix (each role added/removed by each caller role) and both guards.
- [x] 1.2 Refactor `_managing_admin_accounts_forbidden` in `apps/api/app/routers/users.py` to call the shared policy (create + deactivate paths keep current 403 messages/semantics); verify `make api-test` passes with existing `test_user_admin.py`/`test_auth.py` unchanged.

## 2. Replacement endpoint

- [x] 2.1 Add `UserRolesReplace` schema (`roles: list[Role]` unique, empty list allowed per revised design decision 3, optional `group_id`) in `apps/api/app/schemas/user.py` and re-export via schemas `__init__.py`; verify `make typecheck`.
- [x] 2.2 Implement `PUT /users/{user_id}/roles` in `apps/api/app/routers/users.py` with guard ordering from design decision 4, the last-active-system-admin count query, and persistence of `roles` (+`group_id` when supplied); verify router tests in `apps/api/tests/test_role_assignment.py`: dispatcher grants driver in-scope/ out-of-scope 403, dispatcher cannot grant dispatcher 403, company-admin grants dispatcher, company-admin cannot grant company-admin 403, system-admin grants admin roles, self-change 403, invalid role name 422, empty list strips roles (role-less user in group re-granted by dispatcher), deactivated target 404, idempotent replay with same `Idempotency-Key` returns the same result without double-apply (last-system-admin 409 is unreachable through this endpoint - covered by policy unit tests per design decision 4).
- [x] 2.3 Extend `deactivate_user` with the lockout guard (design decision 7): active target holding `system-admin` with no other active system-admin -> 409 and account stays active; verify router test for a lone system-admin self-deactivation plus regression test that deactivation with a second active system-admin still succeeds.

## 3. Verification & docs

- [x] 3.1 Confirm the new operation renders in OpenAPI (`GET /api/openapi.json` with debug on) under the `users` tag with 403/404/409 responses documented; verify by reading the served JSON.
- [x] 3.2 Run `make lint && make typecheck && make api-test` and one end-to-end manual pass against the running dev stack (dispatcher token from `make api-dev` db-seed, `PUT /users/{id}/roles` granting driver, then `/drivers/{id}/group` accepts the driver); report results.
