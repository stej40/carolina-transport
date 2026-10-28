# Design: MVP1 transports & orders

Fields/states per `mvp1-domain-discovery` signed schema; this design fixes
mechanisms that are agnostic to the exact field list.

- **State machine**: single module owning `can_transition(state, event)` +
  legal transition table from discovery; endpoints call it, no state writes
  bypass it. Transports carry current state; all history lives in events.
- **Event log**: `transport_events` (UUID PK, transport_id, actor_id, type,
  before_state, after_state, payload JSONB, created_at). INSERT-only; DB
  revoked UPDATE/DELETE for the app role if feasible.
- **Idempotency**: middleware keyed on (user, `Idempotency-Key`) storing
  request hash -> response; replay returns stored result. Applies to all
  POST/PATCH/DELETE under transport routes.
- **Order editing**: `orders.editable_until_invoice_linked` derived server-side
  (always true while no invoice table exists); billing-field writes rejected
  when false; edits append order-level events to the same log.
- **Multiple transports per order**: `transports.order_id` FK already allows
  1..N; no stored order-level aggregate state (order "done" = all transports
  completed, derived). Splitting goods is logistical - money stays on the
  order (per-transport quantities arrive with MVP3 documents).
- **Two drivers**: join table `transport_drivers` (transport_id, driver_id,
  assigned_by, assigned_at, UNIQUE(transport_id, driver_id)) REPLACES the
  signed schema's `transports.driver_id`; max 2 enforced in service layer.
  Switch = row replace + `transport_events` event with new event_type
  `assignment`; transition endpoints verify the acting driver is currently
  assigned.
- **Currency & portal settings**: `portal_settings` single-row table
  (default_currency CHAR(3) CHECK IN ('CZK','EUR'), updated_at), seeded
  'CZK'; GET + update endpoint under /api/v1/settings; order POST falls back
  to the stored default when currency omitted; order currency validated
  against ('CZK','EUR').
- **Money**: NUMERIC(12,2), currency restricted to CZK/EUR, VAT percent
  integer; rounding policy: round half
  up at line level, amounts summed.
- Group scoping via `scoped_groups` dependency from mvp1-organizational-groups.
