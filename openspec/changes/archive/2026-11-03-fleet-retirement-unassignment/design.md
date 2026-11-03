# Design

## Context

Trucks/trailers share `FleetMixin` (`spz` unique, `group_id` NOT NULL FK) and
one router builder (`app/routers/fleet.py`); write access is
`fleet_writer = dispatcher + admins` and dispatcher visibility is group
membership (`group_in_scope`, `ScopedGroupIds`). Transports reference fleet by
FK with no lifecycle check today (`transports.py:112-123` catches
`IntegrityError` -> 400). Five Alembic revisions exist; tests build SQLite via
`Base.metadata.create_all`. Motivation and matrix decisions (retire, restore,
SPZ freed, unassign) are in proposal.md / spec delta.

## Goals / Non-Goals

**Goals:**
- One migration makes retirement + unassignment expressible on both tables.
- Retire/restore/unassign and new registration are admin-only; the only other
  dispatcher-facing change is that retired/unassigned vehicles become invisible
  to them.
- History is append-only-safe: no operation rewrites transport rows.

**Non-Goals:**
- Hard delete, driver lifecycle, availability scheduling, group-move scope
  validation on transports (existing gap stays), UI changes, PWA changes.

## Decisions

1. **Schema (migration `0006_fleet_retirement`):**
   - `trucks`/`trailers`: add `retired_at TIMESTAMPTZ NULL`; make `group_id`
     nullable (values remain non-null until someone unassigns).
   - Drop the plain unique constraint on `spz`; create partial unique
     `Index("uq_trucks_spz_active", "spz", unique=True, where="retired_at IS
     NULL")` (same for trailers). SQLAlchemy emits this for both PostgreSQL
     (`postgresql_where`) and SQLite (`sqlite_where`, supported since 3.8), so
     `create_all`-based tests and prod agree. Alternatives: app-level
     uniqueness (rejected - races), separate archive table (rejected - breaks
     FK history).
2. **Model:** `FleetMixin` gains `retired_at: Mapped[datetime | None]`,
   `group_id` becomes `Mapped[uuid.UUID | None]`; `FleetOut.group_id` nullable,
   `FleetOut.retired_at` added (visible to admins; dispatchers never receive
   retired rows anyway).
3. **New routes in the shared builder** (all `Depends(admin_only)`, registered
   under each prefix):
   - `DELETE /{resource_id}` -> retire: set `retired_at = utcnow()`, 204,
     replay-safe (retiring a retired row is a silent 204).
   - `POST /{resource_id}/restore` -> 409 "SPZ already in active use" if an
     active row holds the SPZ (pre-check + IntegrityError backstop -> 409);
     otherwise clear `retired_at`, return `FleetOut`.
   - `DELETE /{resource_id}/group` -> unassign: `group_id = NULL`, 204.
   - `GET` list: always filter `retired_at IS NULL`; admin-only optional
     `?include_retired=true` returns retired rows too (admins need it to find
     restore candidates). Unassigned (`group_id IS NULL`) rows appear only for
     unrestricted callers (`scoped is None`) - for dispatchers the current
     `group_id IN scoped` filter already hides them.
   - Existing move: extend `_load_scoped` to 404 on retired rows (must restore
     before moving; avoids half-live state). Dispatcher invisibility of
     unassigned is automatic: `group_in_scope(scoped, None)` is False.
   - Create still requires a group (spec unchanged; admin unassigns after).
4. **Transport attach guard:** where `transports.py` currently relies on
   `IntegrityError`, add explicit validation: if `truck_id`/`trailer_id`
   supplied, load the row; `None` or `retired_at is not None` -> 400 "Unknown
   truck or trailer" (same message for retired and missing - no enumeration).
   Applies to create; there is no transport update path for fleet refs today,
   keep the helper reusable.
5. **Silently = no fan-out:** no notification, no event-log entry in MVP1 (the
   append-only transport event log stays transport-scoped; fleet lifecycle
   visible only via API state).
6. **Registration becomes admin-only (Jiří's follow-up requirement):** the
   shared builder's `POST ""` switches from `FleetCaller` (dispatcher +
   admins) to `admin_only`; the existing group-scope check becomes moot for
   admins (`ScopedGroupIds` is None for them) but is kept unchanged.
   `FleetCreate` still requires `group_id` - an admin registers into a group
   and un-assigns afterwards if needed. Dispatcher move (`PATCH /{id}/group`)
   and list stay dispatcher-capable; only creation rights tighten.
   Alternative: deprecate-then-remove - rejected, the portal has no fleet UI
   yet (grep of dispatcher-web shows no fleet calls), so this is a safe
   breaking change before any consumer exists.
7. **Label editing (review follow-up):** `PATCH /{resource_id}` on the shared
   builder with `FleetUpdate {label: str | None}`; caller is `FleetCaller`
   (dispatcher + admins). Semantics: the `label` key always sets the value
   (`null` clears it). Addressing reuses `_load_scoped`, so retired vehicles
   are 404 and dispatcher blindness to unassigned/foreign vehicles applies
   unchanged. No migration, no schema shape change beyond the request body.

## Risks / Trade-offs

- [Partial unique index in migration must match the model definition or
  tests/prod diverge] → same `where` clause in both; a router test registers
  duplicate SPZ against a retired one (must pass) and against an active one
  (must 409).
- [Retiring a truck still attached to an OPEN transport] → allowed per
  decision; transport keeps showing it, only new assignments are blocked.
  Mitigation: none needed for MVP1 pilot, revisit for scheduling features.
- [`FleetOut` shape change is breaking for API consumers] → no consumer reads
  fleet today (dispatcher-web does not call fleet endpoints; `packages/shared`
  has no generated types yet - the OpenAPI generator arrives with
  mvp1-driver-pwa-online and will pick the new shape up), so this is a
  docs-only break; re-check when the generator lands.
- [Restore after SPZ reuse is forever impossible while active] → intended;
  restore the conflict error tells admins to relabel/retire the new row first.

## Migration Plan

Order: run `alembic upgrade head` (additive, old code compatible) → deploy API
→ regenerate shared types. Rollback: revert deployment; columns can stay
(partial index reverts with `alembic downgrade -1`).
