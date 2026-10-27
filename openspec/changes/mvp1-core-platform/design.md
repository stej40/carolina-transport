# Design: MVP1 core platform

Migrated from `docs/planning/mvp1-implementation-plan.md` (locked decisions
section) and translated to English. See `openspec/config.yaml` context for the
full list of locked technical decisions.

## Architecture overview

```
driver PWA (offline-first, Dexie outbox)      dispatcher web (TanStack Query)
        │  presigned PUT (photos/PDFs)  │            │ REST /api/v1 (JWT)
        ▼                               ▼            ▼
     Garage 2.4 (S3)  ◄── verify ──  FastAPI  ──  PostgreSQL 18 (asyncpg)
                                      │
                                      └── append-only event log
```

- API is the single source of truth; storage is direct-to-Garage via presigned
  URLs so photo bytes never transit the app server.
- All mutating endpoints require an `Idempotency-Key`; safe for outbox replay.
- Transport state transitions are validated by one state machine module and
  every transition appends to `transport_events` (immutable, UUID PK, actor,
  before/after state, payload JSONB, server timestamp).

## Data model direction (to be finalized in M2 discovery)
Core entities: `users`, `groups`, `group_members` (dispatcher <-> group),
`trucks` (SPZ, assigned group), `orders`, `transports`, `transport_events`,
`document_types`, `documents` (+ `document_reviews`), `external_ids`
(system, entity_type, entity_id, external_id). Orders and transports carry
`group_id`; a transport inherits the group of its order. Drivers are `users`
with role `driver` assigned to exactly one group; trucks belong to one group.
Constraints:
- UUID PKs generated client-side when offline creation is possible.
- Money as NUMERIC; one agreed rounding policy.
- `documents.data` is JSONB free-form attributes per document type; OCR (MVP3)
  will fill it later, so structure must not fight that.
- Orders carry billing fields (quantity, unit, unit price, currency, VAT,
  billing text) now, even though invoicing ships in MVP2.

## Offline sync design
- PWA keeps local drafts in IndexedDB (Dexie) with a durable outbox queue.
- Mutations are applied locally immediately, synced opportunistically.
- Conflict guards: state transitions are conditional on expected current
  state ("compare-and-set"); document uploads use presigned URLs fetched at
  sync time.

## Auth
Own JWT module: short-lived access tokens, rotating refresh tokens stored
hashed, argon2 password hashes, role claims from `driver` / `dispatcher` /
`company-admin` / `system-admin`, seed script for the first users, admin
user-management endpoints (create/deactivate; only system-admin manages admin
accounts). Group scoping is enforced in queries, not just by role (see
organizational-groups).

## Open question for M2
- Is a transport tied to a specific truck (weighbridge tickets carry SPZ)?
  If yes, `transports.truck_id` joins the schema in M2; MVP1 keeps trucks as
  group master data only.

## Deployment
Docker Compose on a self-hosted VPS: postgres:18-alpine, garage:2.4 (single
node dev config `infra/garage.toml`), api, static frontends; Caddy for TLS;
nightly `pg_dump` + Garage bucket mirror to a second bucket; runbook in
`docs/runbook/` (added at M8).

## Deferred, with plug-in points reserved
| Feature | MVP | Plug-in point |
|---|---|---|
| POHODA invoice write + e-mail | MVP2 | `APPROVED` transition event → outbox job → `integrations/pohoda/` adapter |
| Bank payment pairing | MVP4 | daily statement import → match VS + amount |
| OCR extraction | MVP3 | fills `documents.data` JSONB, human confirms |
| AI assistant (LangChain/MCP) | MVP5 | MCP server over `/api/v1` reads + event log |
| Native apps | later | reuse `/api/v1` OpenAPI contract |
| Push notifications (FCM/APNs) | later | assignment transitions already in the event log become the trigger; a future change adds device-token registration + dispatch. MVP1 ships in-app badge only |

## Addenda from scope discussion (2026-10-26)
- **Order editing**: editable until an invoice is linked. In MVP1 no invoice
  entity exists yet, so editing is effectively always allowed; the API MUST
  nevertheless model editability as a server-side check so the MVP2 invoice
  link can tighten it without contract change. Every edit is appended to the
  transport/order event log like any material change.
- **Localization**: `react-i18next` in both frontends; catalogs live per app.
  Initial language = user profile preference (cs/en/de) fetched after login;
  fallback English (portal) / Czech (PWA). Changing it PATCHes the profile.

## Key risks & mitigations
- Offline sync complexity → deferred to M7 behind a forced-from-M3
  outbox+idempotency design.
- Driver adoption → giant-button UX, pilot with 2–3 drivers (M8).
- Paperwork reality ≠ assumptions → M2 discovery gate before domain code;
  schema proposal requires Jiří's sign-off.
- Legal status of photographed documents (metrical requirements, tax
  eligibility) → flag in M2; design keeps both outcomes open (paper originals
  may remain in use).
