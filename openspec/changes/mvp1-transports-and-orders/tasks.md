# Tasks: MVP1 transports & orders

## Schema & models
- [ ] Alembic: `orders`, `transports`, `transport_events`, `external_ids`
- [ ] Models with UUID PKs (client-generatable), NUMERIC money fields

## API
- [ ] Order CRUD with billing-ready field validation + group scoping
- [ ] Order edit endpoint with server-side editability check, edits logged
- [ ] Driver assignment (same-group check via scoped helper)
- [ ] State machine module + transition endpoints per signed schema
- [ ] Append-only event log writes on every transition and material change
- [ ] Idempotency-Key middleware on all write endpoints
- [ ] GET transport history

## Tests
- [ ] API test per allowed and forbidden state transition
- [ ] Idempotent replay returns original result, no duplicate
- [ ] Cross-group order not visible (as-if-absent)
