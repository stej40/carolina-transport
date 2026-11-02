# Design

## Context

Roles live in `users.roles` (JSON list, `app/models/user.py:20`); no DB change
is needed. Authorization today is `require_roles(...)` (`app/deps.py:46`) plus
one bespoke check `_managing_admin_accounts_forbidden` (`routers/users.py:19`).
`UserCreate` accepts `Role = Literal[...4 roles]` (`app/schemas/common.py:6`).
Dispatchers' groups come from `GroupMember` via `get_scoped_group_ids`
(`deps.py:69`); a driver's home group is `users.group_id`. The
`/drivers/{id}/group` endpoint requires the target to already hold `driver`,
which is why granting must optionally carry a home group. See proposal.md - Why.

## Goals / Non-Goals

**Goals:**
- One pure policy function is the single source of truth for the matrix; the
  router only translates its result to HTTP.
- Guards ordered so error semantics are stable regardless of input order.

**Non-Goals:**
- No role hierarchy inheritance, no per-group dispatcher-role scoping
  (dispatcher stays global for reads as today), no audit trail beyond the
  existing idempotency rows.

## Decisions

1. **`app/role_policy.py` - pure function, no DB types beyond dataclasses.**
   `evaluate_role_change(caller_roles, caller_group_ids|None, target_roles,
   desired_roles, target_group_id, caller_id, target_id,
   other_active_system_admins: bool) -> list[str]` returns reason codes (empty
   list = allowed). Router maps codes → HTTP: `self-change` 403,
   `authority` 403, `scope` 403, `last-system-admin` 409.
   Why not a pydantic validator: the matrix depends on both target and caller
   plus DB-derived facts; a data-level pure function is exhaustively unit-testable.
   Alternative `deps.py` helper returning HTTPException - rejected: couples
   policy to transport and blocks table-driven unit tests.
2. **Diff-based matrix.** Compute `added = desired - current`,
   `removed = current - desired`; every touched role (union) must pass the
   caller's grant-authority for that role (revocation symmetric per proposal).
   Authority table as a module constant:
   `{"driver": {"dispatcher","company-admin","system-admin"}, "dispatcher":
   {"company-admin","system-admin"}, "company-admin": {"system-admin"},
   "system-admin": {"system-admin"}}`. Replaces the ad-hoc
   `_managing_admin_accounts_forbidden` in `users.py` (also reused by
   create/deactivate paths - same behavior, now shared).
3. **Request schema** `UserRolesReplace { roles: list[Role] (may be empty,
   unique), group_id: UUID | None }`. Asymmetry with `UserCreate` (min one
   role) is deliberate: an empty role list is already storable (`users.roles`
   defaults to `[]`) and is the only way revoke-then-regrant becomes
   meaningful for dispatchers, who may not touch any other non-protected role
   (decided after Jiří's review: option 1). An empty list leaves the account
   active but privileged-endpoint-free: sign-in, token refresh and `/auth/me`
   keep working, while every role-gated business endpoint returns 403. `group_id` is honored by policy only as *effective home
   group* input for the dispatcher-scope rule; the endpoint persists
   `group_id` alongside roles (validated group exists and, for admin
   callers too, exists - moving a driver's group for admins already possible
   via `/drivers/{id}/group`, keeping this path consistent). Invalid role
   names fail at pydantic (422) before policy runs.
4. **Guard ordering in the router:** auth (`require_roles("dispatcher",
   *ADMIN_ROLES)`) → schema validation (422 for unknown role names) → load
   target (404 incl. `is_active`) → self-change (403) → policy evaluation →
   commit; an empty `roles` list is a valid strip-all request, not an error.
   `last-system-admin`
   check needs one query: `SELECT roles FROM users WHERE is_active AND id <>
   target`, evaluated in Python (portable SQLite/Postgres), only when
   `system-admin in removed`. Note: through the roles endpoint the 409 is
   defense-in-depth only - the matrix forces the caller to be a *second* active
   system-admin, so the guard can never fire there; it becomes reachable on the
   deactivation path (see decision 7).
5. **Idempotency:** plain `PUT` with `Idempotency-Key` like other writes
   (middleware already global); replace-semantics make replays harmless.
6. **Seed script unchanged** - documented escape hatch for the self-change /
   bootstrap cases (first system-admin); README pointer in code comment only.
7. **Lockout guard on deactivation (added after Jiří's review of option 1):**
   `deactivate_user` reuses the same "other active system-admins" query; when
   the (active) target holds `system-admin` and none other exists, respond 409
   "cannot deactivate the last active system-admin account". Company/system-admin
   authority over admin targets already enforced there via the shared
   `denied_roles` helper; only the last-holder case is new.

## Risks / Trade-offs

- [Dispatcher could make someone driver and thus PWA-visible within their
  group] → acceptable per agreed matrix; home-group requirement keeps scope
  tight.
- [`group_id` writable via this endpoint duplicates `/drivers/{id}/group`]
  → same policy checks reused in the shared function; risk of drift mitigated
  by router tests hitting both paths.
- [Admin accidentally demotes last system-admin via API] → 409 guard; seed
  script remains the (logged-out) recovery path, matching current ops runbook.
- [Matrix drift vs dispatcher-web UI gating later] → OpenAPI is contract; UI
  change is separate future change.

## Migration Plan

Additive endpoint, no schema/migration. Rollback = drop the route; no data
format change. Deploy: nothing operator-side beyond normal release.
