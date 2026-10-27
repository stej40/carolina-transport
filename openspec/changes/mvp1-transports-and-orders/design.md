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
- **Money**: NUMERIC(12,2), VAT percent integer; rounding policy: round half
  up at line level, amounts summed.
- Group scoping via `scoped_groups` dependency from mvp1-organizational-groups.
