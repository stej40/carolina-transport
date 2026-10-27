# Proposal: MVP1 transports & orders

## Why
Orders and transports are the domain core everything else hangs on: a
dispatcher books work, a driver executes it, and every transition must be
auditable (event log) and offline-replay-safe (idempotency) from day one -
cheap now, very expensive to retrofit later.

## What Changes
- New capability `transport-lifecycle`: order CRUD (billing-ready fields per
  signed schema), order editing until invoice-linked (invoice entity does not
  exist in MVP1; server-side editability check reserved for MVP2), driver
  assignment restricted to the order's group, transport state machine with
  transition validation, append-only event log, Idempotency-Key middleware on
  all write endpoints, UUID PKs (client-generatable), NUMERIC money.
- Tables: `orders`, `transports`, `transport_events` (+ `external_ids`
  scaffold per config constraints).

## Out of scope
Documents (mvp1-document-collection), invoicing/POHODA (MVP2), portal and PWA
UI (later changes), OCR.

## Capabilities
### New Capabilities
- `transport-lifecycle`

### Modified Capabilities
(none)

## Impact
- `apps/api`: domain routers, state machine module, event log, idempotency
  middleware; Alembic migrations; generated API types in `packages/shared`.

**Depends on:** `mvp1-domain-discovery` sign-off, `mvp1-organizational-groups`.
