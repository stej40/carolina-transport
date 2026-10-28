# Tasks: MVP1 transports & orders

## Schema & models
- [ ] Alembic: `orders`, `transports`, `transport_events`, `transport_drivers`,
  `portal_settings`, `external_ids`
- [ ] Models with UUID PKs (client-generatable), NUMERIC money fields

## API
- [ ] Order CRUD with billing-ready field validation + group scoping
- [ ] Order currency validation CZK/EUR + default from portal settings when
      omitted
- [ ] Order edit endpoint with server-side editability check, edits logged
- [ ] Create transport on order (1..N transports per order)
- [ ] Driver assign/replace endpoints: same-group check, max 2 per transport,
      switch logged as assignment event
- [ ] Transition endpoints verify acting driver is currently assigned
- [ ] GET + update portal settings endpoint (default_currency)
- [ ] State machine module + transition endpoints per signed schema
- [ ] Append-only event log writes on every transition and material change
- [ ] Idempotency-Key middleware on all write endpoints
- [ ] GET transport history

## Tests
- [ ] API test per allowed and forbidden state transition
- [ ] Idempotent replay returns original result, no duplicate
- [ ] Cross-group order not visible (as-if-absent)
- [ ] Third driver on a transport rejected
- [ ] Driver swap during in-transit updates both active lists + event log
- [ ] Currency-less order creation uses stored default; non-CZK/EUR rejected
- [ ] Two transports on one order transition independently
