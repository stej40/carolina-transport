# Design: Idempotency for all write endpoints

Context: middleware exists (`app/idempotency.py`) with an allow-list of
domain prefixes and an optional header. See proposal.md - Why for the
invariant this closes.

## Decisions

- **Auth endpoints excluded (deny-by-exception).** The replay cache stores
  response bodies as plaintext JSONB. Login/refresh responses contain raw
  access + refresh tokens; caching them would put plaintext credentials at
  rest, undoing the design that stores only refresh-token **hashes**, and
  replay semantics are wrong for rotating tokens (the stored pair is stale).
  Duplicate logins are also benign (extra hash rows, revocation handles
  them). Alternative considered: exclude only `/auth/refresh` and encrypt
  stored bodies - rejected as complexity without real risk reduction.
- **Required header (400), not optional.** The project invariant "keys on
  all write endpoints" must be structural; an optional key makes safety a
  client convention and duplicate orders the failure mode. The breaking
  change costs nothing now (portal/PWA unimplemented) and is documented as
  the client contract for `mvp1-offline-sync`'s outbox (one key per intended
  operation, reused across retries). Non-2xx outcomes remain un-stored so
  the client may retry with the same key after a transient failure.
- **Scope inversion.** Replace the `DOMAIN_PREFIXES` allow-list with "all
  `/api/v1` writes except `/api/v1/auth/`". PUT/DELETE are state-convergent
  but still included because every accepted write emits audit/event rows -
  replay would duplicate the audit trail. The (user, key) namespace and
  method+path+body request hash stay as-is: cross-endpoint key reuse returns
  422 (conflict), never a silent hit.
- **Retention.** A small `DELETE FROM idempotency_keys WHERE created_at <
  now - 30 days` at startup. Bounded table, no scheduler, no new infra. Risk
  is accepted: an outbox replaying after 30 days offline could duplicate -
  the driver PWA sync window is hours to days, and that policy will be
  revisited if `mvp1-offline-sync` needs a longer horizon.

## Risks / Trade-offs
- [400-on-missing-key breaks ad-hoc curl usage] → error message names the
  header and its purpose; tests demonstrate the pattern.
- [Startup purge races multiple API replicas] → DELETE is idempotent.
