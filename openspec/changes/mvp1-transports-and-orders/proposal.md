# Proposal: MVP1 transports & orders

## Why
Orders and transports are the domain core everything else hangs on: a
dispatcher books work, a driver executes it, and every transition must be
auditable (event log) and offline-replay-safe (idempotency) from day one -
cheap now, very expensive to retrofit later.

## What Changes
- New capability `transport-lifecycle`: order CRUD (billing-ready fields per
  signed schema), order editing until invoice-linked (invoice entity does not
  exist in MVP1; server-side editability check reserved for MVP2), an order
  MAY have more than one transport (goods split across vehicles; billing
  stays on the order), driver assignment restricted to the order's group with
  at most two drivers per transport and mid-ride switch (event-logged),
  transport state machine with transition validation, append-only event log,
  Idempotency-Key middleware on all write endpoints, UUID PKs
  (client-generatable), NUMERIC money, currencies limited to CZK/EUR.
- New capability `portal-settings`: company-wide portal configuration -
  default currency served to the dispatcher portal for order creation.
- Tables: `orders`, `transports`, `transport_events`, `transport_drivers`
  (replaces single `transports.driver_id` from the signed schema),
  `portal_settings` (+ `external_ids` scaffold per config constraints).

## Out of scope
Documents (mvp1-document-collection), invoicing/POHODA (MVP2), portal and PWA
UI (later changes), OCR, per-transport quantity split (arrives with
weighbridge documents/OCR in MVP3), settings & currency UI (dispatcher portal
change).

## Capabilities
### New Capabilities
- `transport-lifecycle`
- `portal-settings`

### Modified Capabilities
(none)

## Impact
- `apps/api`: domain routers, state machine module, event log, idempotency
  middleware; Alembic migrations; generated API types in `packages/shared`.

**Depends on:** `mvp1-domain-discovery` sign-off, `mvp1-organizational-groups`.
