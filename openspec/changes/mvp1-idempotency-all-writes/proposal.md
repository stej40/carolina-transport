# Proposal: Idempotency for all write endpoints

## Why
Project constraint 4 requires idempotency keys on **all** write endpoints so
offline outbox replays are safe, but the middleware currently covers only the
domain routes (`/orders`, `/transports`, `/settings`) and treats the header as
optional. A client that forgets the key silently creates duplicates - the
worst failure mode in a system that will invoice these orders. No frontend
client exists yet, so enforcing the invariant now is nearly free.

## What Changes
- Idempotency middleware applies to every `POST/PATCH/PUT/DELETE` under
  `/api/v1`, excluding `/api/v1/auth/*`.
- **BREAKING (future clients only, none exist yet):** a write request without
  an `Idempotency-Key` header is rejected with 400.
- Auth token endpoints (login/refresh/logout) are explicitly exempt: their
  responses are credentials and MUST NOT be written to the plaintext replay
  cache (`idempotency_keys.response`), preserving refresh-token-hashes-only
  at rest.
- Retention: stored replay rows older than 30 days are purged at API startup
  (no new infrastructure).
- Existing endpoint tests (users/groups/fleet) updated to send keys; no
  router code changes (the middleware is generic).

## Out of scope
Auth token rotation/revocation redesign, driver-PWA outbox implementation
(mvp1-offline-sync), dispatcher portal UI, key-namespace changes beyond the
current (user, key) scheme, introducing any external store.

## Capabilities
### New Capabilities
(none)

### Modified Capabilities
- `transport-lifecycle`: the "Idempotent writes" requirement is widened from
  transport write endpoints to all non-auth API writes, gains the
  missing-key (400) and conflicting-key (422) behaviors, and documents the
  auth exemption.

## Impact
- `apps/api`: `app/idempotency.py` (scope inversion + required header),
  `app/main.py` (startup purge), auth router untouched; tests across
  `apps/api/tests/`; OpenAPI error descriptions on write endpoints unchanged
  contract-wise (header documented via middleware response headers).

**Depends on:** `mvp1-transports-and-orders` (archived - the middleware and
`idempotency_keys` table exist).
