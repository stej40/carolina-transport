# Tasks: MVP1 transports & orders

## Schema & models
- [x] Alembic: `orders`, `transports`, `transport_events`, `transport_drivers`,
  `portal_settings`, `external_ids`, `idempotency_keys`
- [x] Models with UUID PKs (client-generatable), NUMERIC money fields

## API
- [x] Order CRUD with billing-ready field validation + group scoping
- [x] Order currency validation CZK/EUR + default from portal settings when
      omitted
- [x] Order edit endpoint with server-side editability check, edits logged
- [x] Create transport on order (1..N transports per order)
- [x] Order cancel endpoint: cascade to not-yet-completed transports,
      cancelled state terminal, events logged
- [x] Driver assign/replace endpoints: same-group check, max 2 per transport,
      switch logged as assignment event
- [x] Transition endpoints verify acting driver is currently assigned
- [x] GET + update portal settings endpoint (default_currency)
- [x] State machine module + transition endpoints per signed schema
- [x] Append-only event log writes on every transition and material change
- [x] Idempotency-Key middleware on all write endpoints
- [x] GET transport history

## Tests
- [x] API test per allowed and forbidden state transition
- [x] Idempotent replay returns original result, no duplicate
- [x] Cross-group order not visible (as-if-absent)
- [x] Third driver on a transport rejected
- [x] Driver swap during in-transit updates both active lists + event log
- [x] Currency-less order creation uses stored default; non-CZK/EUR rejected
- [x] Two transports on one order transition independently
- [x] Cancel order cascades (assigned/in-transit cancelled, completed
      untouched); cancelled transport rejects transitions and assignments
