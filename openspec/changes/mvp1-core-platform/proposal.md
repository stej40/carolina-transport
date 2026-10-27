# Proposal: MVP1 core platform

## Why
The office worker ("Karolina") who sorts driver paperwork, enters orders into
POHODA, issues invoices, and pairs payments is leaving on maternity leave.
MVP1 removes paper from the loop: dispatchers manage transports and documents
in a web portal, drivers capture statuses and paperwork in an offline-first
PWA, so the office function becomes review-and-approve instead of manual
transcription.

## What Changes
- New FastAPI backend (`/api/v1`) with JWT auth, RBAC (driver, dispatcher,
  company-admin, system-admin), PostgreSQL persistence, and S3 (Garage)
  presigned document uploads.
- New organizational model: **groups** as dispatcher workspaces linking
  drivers and trucks; orders and transports are group-scoped, dispatchers see
  only their groups, company-admins all of it.
- New transport domain: orders, transports with an explicit state machine and
  an immutable event log.
- New document domain: data-driven document taxonomy, presigned photo/PDF
  upload, dispatcher approve/reject loop, completeness checks per transport.
- New dispatcher web portal (React + TS + Vite): dashboard per state, create
  and edit orders, assign driver, transport detail with document review.
- New driver PWA (offline-first): login, current transport, in-app
  notification of new assignments, status actions, camera capture to Garage,
  outbox sync with idempotency keys.
- UI localization: Czech/English/German, selected per user and stored on the
  user profile, applied in both frontends.
- Self-hosted deployment (Docker Compose + Caddy/TLS, pg_dump + S3-mirror
  backups) and a 2-3 driver pilot.

## Out of scope
POHODA integration (MVP2), OCR/AI extraction (MVP3), bank payment pairing
(MVP4), AI assistant/MCP server (MVP5), native iOS/Android, push notifications.
The data model MUST nevertheless be ready for all of these (billing-ready
orders, variable symbol, external-ID mapping, event log).

## Capabilities
### New Capabilities
- `identity-auth`: user accounts, JWT access/refresh tokens, RBAC roles
  (driver, dispatcher, company-admin, system-admin), admin user management.
- `organizational-groups`: groups as dispatcher workspaces linking drivers
  and trucks; group-scoped orders/transports and visibility.
- `transport-lifecycle`: orders, transport assignment, state machine,
  immutable event log.
- `document-collection`: document taxonomy, uploads, review workflow,
  completeness.
- `dispatcher-portal`: web UI for dispatchers.
- `driver-pwa`: offline-first mobile PWA for drivers, incl. in-app
  assignment notification.
- `ui-localization`: per-user language selection (cs/en/de) across frontends.
- `platform-deployment`: self-hosted stack, backups, operational health.

### Modified Capabilities
(none - first functional change)

## Impact
- Apps: `apps/api` (grows from healthcheck scaffold), `apps/dispatcher-web`,
  `apps/driver-pwa`, `packages/shared` (generated API types).
- Infra: `infra/docker-compose.yml` (postgres, garage, api), Caddy in prod.
- Database: Alembic migrations from scratch; schema per design.md constraints.
