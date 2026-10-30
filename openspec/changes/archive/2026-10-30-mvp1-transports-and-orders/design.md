# Design: MVP1 transports & orders

Fields/states per `mvp1-domain-discovery` signed schema; this design fixes
mechanisms that are agnostic to the exact field list.

- **State machine**: single module owning `can_transition(state, event)` +
  legal transition table from discovery; endpoints call it, no state writes
  bypass it. Transports carry current state; all history lives in events.
  Binding machine (discovery §2): draft →(assign) assigned →(arrive_loading)
  at_loading →(start_transit) in_transit →(arrive_unloading) at_unloading
  →(finish_unloading) completed →(hand_in_documents) in_review
  →(accept) ready_for_invoicing | (reject) returned →(resubmit) in_review;
  unassign: assigned → draft; cancel: draft/assigned → cancelled;
  order_cancelled (system event, fired only by the order-cancel cascade):
  draft/assigned/at_loading/in_transit/at_unloading → cancelled. `cancelled`
  is terminal. Review events (accept/reject/resubmit) stay in the table so
  document-collection's review endpoints can fire them.
- **Event log**: `transport_events` (UUID PK, transport_id FK nullable,
  order_id FK nullable - exactly one set, CHECK xor; actor_id, type
  (`state_change`\|`assignment`\|`note`), before_state, after_state, payload
  JSON, occurred_at). INSERT-only; DB revoked UPDATE/DELETE for the app role
  if feasible. Order-level edit/cancel events use the `order_id` side of the
  same table ("edits append order-level events to the same log").
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
  assigned; removing the last driver fires `unassign` (assigned → draft),
  adding a second to a draft transport fires `assign` (draft → assigned).
- **Order cancellation**: `orders.cancelled_at` TIMESTAMPTZ NULL; cancel
  endpoint sets it and moves every transport that has not yet reached
  `completed` (states draft, assigned, at_loading, in_transit, at_unloading)
  to `cancelled` via the `order_cancelled` machine event, appending a
  state-change event per transport with the dispatcher as actor; transports
  past `completed` (in_review, returned, ready_for_invoicing) keep their
  state. Terminal: transition, assign, and create-transport endpoints reject
  cancelled orders/transports; no reactivation path in MVP1; second cancel
  returns 409.
- **Currency & portal settings**: `portal_settings` single-row table
  (default_currency CHAR(3) CHECK IN ('CZK','EUR'), updated_at), seeded
  'CZK'; GET + update endpoint under /api/v1/settings; order POST falls back
  to the stored default when currency omitted; order currency validated
  against ('CZK','EUR').
- **Money**: NUMERIC(12,2), currency restricted to CZK/EUR, VAT percent
  integer; rounding policy: round half
  up at line level, amounts summed.
- Group scoping via `scoped_groups` dependency from mvp1-organizational-groups.
