# Tasks

## 1. Schema and models

- [x] 1.1 Write Alembic revision `0006_fleet_retirement` per design decision 1 (add `retired_at` to trucks/trailers, make `group_id` nullable, replace SPZ unique index with partial unique on `retired_at IS NULL` for both tables, downgrade included); verify with `uv run alembic upgrade head` + `downgrade -1` + `upgrade head` against the local dev Postgres and inspect the resulting indexes.
- [x] 1.2 Update `FleetMixin` (nullable `group_id`, `retired_at`) and `FleetOut` (`group_id: UUID | None`, `retired_at: datetime | None`); verify `make typecheck` and `make api-test` pass with existing fleet tests (adjust fixtures only where they assert non-null group).

## 2. Fleet lifecycle endpoints

- [x] 2.1 Add admin-only `DELETE /{resource_id}` (retire), `POST /{resource_id}/restore`, `DELETE /{resource_id}/group` (unassign) to the shared router builder, plus list filter (`retired_at IS NULL` default, `?include_retired=true` admins only, unassigned rows only for unrestricted callers); verify router tests in `apps/api/tests/test_fleet_lifecycle.py`: retire hides from dispatcher listing + returns 204 to admin, dispatcher gets 403 on all three actions, re-register retired SPZ succeeds, duplicate active SPZ still 409, restore clears retired_at, restore conflict returns 409 unchanged, unassigned truck invisible to group dispatcher and visible to company-admin.
- [x] 2.2 Exclude retired rows from `_load_scoped` (move must restore first) and keep dispatcher blindness to unassigned via `group_in_scope`; verify with a move test on retired -> 404 and a reassign-by-admin test.
- [x] 2.3 Switch the shared builder's `POST ""` registration to `admin_only` per design decision 6; verify tests that dispatcher `POST /trucks` and `POST /trailers` return 403 with no record created while company-admin/system-admin registration still returns 201, and update existing fleet tests (e.g. `test_organizational_groups.py`) whose fixtures register trucks with a dispatcher token to use an admin token.
- [x] 2.4 Add `PATCH /{resource_id}` label update to the shared builder per design decision 7 (`FleetUpdate.label`, `FleetCaller`, `_load_scoped` addressing); verify tests in `test_fleet_lifecycle.py`: dispatcher relabels own-group truck (200 + new label, `null` clears), foreign dispatcher 404, retired vehicle 404, admin relabels unassigned vehicle 200; re-run `make lint && make typecheck && make api-test`.

## 3. Transport attach guard

- [x] 3.1 Validate `truck_id`/`trailer_id` in transport create (helper per design decision 4): missing or retired -> 400 "Unknown truck or trailer"; verify tests that creating a transport with a retired truck is rejected, an active truck still works, and a previously-saved transport listing a retired truck still renders it.

## 4. Integration

- [x] 4.1 Confirm no frontend consumer breaks from the `FleetOut` change (grep `apps/dispatcher-web/src` + `apps/driver-pwa/src` for truck/trailer/`group_id` - none expected; generated types land with mvp1-driver-pwa-online) and run `make lint && make typecheck && make api-test`; verify all three pass.
- [x] 4.2 End-to-end on the dev stack (`make infra-full`, admin token): register truck -> unassign -> dispatcher cannot see -> reassign -> retire -> SPZ re-registration -> restore conflict -> restore after retiring the twin; verify each step's HTTP status via curl against :8000.
