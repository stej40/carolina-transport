# Proposal: Fleet retirement and group unassignment

## Why

Trucks and trailers today can only be registered, listed and moved between
groups; there is no way to take a vehicle out of service, and every
truck/trailer is permanently welded to a group (`group_id` NOT NULL). Jiří
needs company-admins and system-admins to silently delete (retire) fleet from
the portal and to remove vehicles from groups, while transport history keeps
referencing the vehicles that actually ran.

## What Changes

- Retire (soft delete) `DELETE /trucks/{id}` and `DELETE /trailers/{id}`, and
  restore via `POST /{kind}/{id}/restore` — company-admin/system-admin only.
  Retired vehicles disappear from dispatcher views and cannot be attached to
  new transports, but rows are kept and past transports continue to show them.
  Restore is allowed unless the SPZ has meanwhile been re-registered.
- SPZ uniqueness becomes *active-only*: retiring frees the SPZ for immediate
  re-registration (partial unique index).
- Un-assign from group: `DELETE /trucks/{id}/group`, `DELETE /trailers/{id}/group`
  — admins only; sets the vehicle to a new admin-only "unassigned" state
  (`group_id` nullable). Unassigned vehicles stay invisible to dispatchers and
  are re-assignable by admins via the existing move endpoint.
- Label editing: `PATCH /trucks/{id}`, `PATCH /trailers/{id}` update the
  free-text `label` — dispatchers within their own groups, admins anywhere;
  retired and out-of-scope vehicles are not addressable.
- **BREAKING (behavior)**: registering a new truck or trailer becomes
  company-admin / system-admin work only - dispatchers lose the current ability
  to `POST /trucks` / `POST /trailers` (they keep moving vehicles between their
  own groups).
- **BREAKING (schema)**: `FleetOut.group_id` becomes nullable and gains
  `retired_at`; Alembic migration adds the columns + swaps the SPZ unique index.

Out of scope: hard delete of fleet rows, driver unassignment/retirement,
vehicle availability scheduling, dispatcher self-service for any of this,
retiring trucks referenced by *open* transports (allowed silently — history
keeps the reference; blocking is not required by the request), UI screens.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `organizational-groups`:
  - MODIFIED "Truck master data" / "Trailer master data" — a vehicle belongs
    to *at most* one group; lifecycle refers to the new retirement requirement.
  - ADDED "Fleet registration restricted to administrators" — dispatchers lose
    registration rights.
  - ADDED "Fleet retirement" — retire/restore, admin-only, active-only SPZ
    uniqueness, invisibility to dispatchers, exclusion from new assignments,
    preserved history.
  - ADDED "Fleet unassignment" — admin-only remove-from-group, unassigned
    state visibility, reassignment path.

## Impact

- `apps/api/app/models/fleet.py` (nullable group, retired_at), new Alembic
  revision `0006_...` (partial unique index on spz), `app/routers/fleet.py`
  (shared builder gains 3 admin routes + list filter; registration dependency
  changes from dispatcher+admin to admin-only), `app/schemas/fleet.py`.
- `app/routers/transports.py` — validate truck/trailer refs are active
  (current FK catch stays as backstop).
- Tests: fleet router tests + migration round-trip; existing fleet/group tests
  updated for nullable `group_id`.
