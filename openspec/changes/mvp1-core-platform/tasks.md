# Tasks: MVP1 core platform

Milestones migrated from `docs/planning/mvp1-implementation-plan.md`.
Status reflects the repository as of migration time.

## M0 - Monorepo scaffold (DONE)
- [x] pnpm workspace + uv backend, Vite apps, infra compose (postgres:18, garage), Makefile targets dev/test/lint/typecheck
- [x] `/api/v1/health` endpoint with smoke test (`apps/api/scripts/smoke_s3.py` verifies Garage presigned S3)

## M1 - Auth & users
- [x] JWT access/refresh token flow with rotation
- [x] RBAC roles dispatcher/driver enforced on all endpoints
- [x] argon2 password hashing, user seed script
- [x] User profile with language preference (cs/en/de, validated) + authenticated
      profile endpoint incl. PATCH of preference
- [x] Auth tests covering happy paths and rejections
- [x] Expand roles to driver/dispatcher/company-admin/system-admin (models,
      seed, RBAC deps) + admin user-management endpoints (create/deactivate)

## M2 - Domain discovery (planning only, no code)
- [ ] Gather anonymized paperwork samples (Jiří): objednávka, vážní lístek nakládka/výkladka, čištění korby, others
- [ ] Recorded walkthrough with process-knowledge holder (checks, blockers, completeness rules)
- [ ] Confirm POHODA edition + VS practice; volumes; bank statement format
- [ ] Confirm group reality: how many groups, who owns membership, are
      transports tied to a specific truck (SPZ on weighbridge tickets)?
- [ ] Deliver: document taxonomy + required attributes
- [ ] Deliver: transport state machine validated against real workflow
- [ ] Deliver: schema proposal document signed off by Jiří (hard gate for M3+)

## M3 - Core CRUD + state machine + event log
- [ ] UUID PKs, client-generatable; NUMERIC money
- [ ] Orders (billing-ready fields) and transports CRUD under /api/v1
- [ ] Order editing: server-side editability check (until invoice linked - always
      true in MVP1), edits appended to event log
- [ ] State machine with transition validation + immutable event log
- [ ] Idempotency-Key middleware on all write endpoints
- [ ] Groups + trucks master data: groups, group_members, trucks tables;
      group_id on orders/transports; group-scoped query layer
- [ ] API tests per allowed and forbidden state transition

## M4 - Dispatcher portal
- [ ] Dashboard grouped by transport state with attention indicators, scoped
      to the dispatcher's groups (group filter for multi-group users)
- [ ] Order creation form enforcing billing fields (acting in a group)
- [ ] Order edit form (fields disabled per server editability response)
- [ ] Driver assignment restricted to same group; transport detail view
- [ ] Dispatcher group-resource management: assign/move drivers & trucks
      between own groups, register trucks, multi-group switcher
- [ ] Company-admin area: manage groups, dispatcher memberships, drivers,
      trucks, users; browse all orders and transports
- [ ] Portal i18n (react-i18next, cs/en/de; profile preference applied, English
      fallback; language switcher persists to profile)
- [ ] End-to-end test of order → assign → in-transit → completed

## M5 - Documents
- [ ] document_types taxonomy as data with required attributes
- [ ] Presigned direct-to-Garage upload flow
- [ ] Approve / reject-with-reason loop; versioned resubmissions
- [ ] Completeness check per transport; e2e test incl. missing-doc flow

## M6 - Driver PWA (online)
- [ ] Login + current transport view with large-touch UX
- [ ] In-app assignment notification: unread badge + highlighted new transport
      after sync, acknowledged on open
- [ ] PWA i18n (react-i18next, cs/en/de; profile preference applied, Czech
      fallback; language switcher persists to profile)
- [ ] Status actions; camera capture → presigned upload
- [ ] Tested on a real phone

## M7 - Offline-first
- [ ] IndexedDB (Dexie) cache + durable outbox queue
- [ ] Offline document queue: pending-sync captures, deferred exactly-once
      upload, sync status in PWA
- [ ] Sync manager with compare-and-set conflict guards
- [ ] Airplane-mode Playwright test proving exactly-once sync

## M8 - VPS deploy + pilot
- [ ] Caddy/TLS + compose production stack; runbook in docs/runbook/
- [ ] Backups: pg_dump cron + Garage mirror to second bucket; restore drill
- [ ] Healthcheck monitoring with operator alerting
- [ ] Pilot with 2–3 drivers running

## Definition of Done (MVP1)
A dispatcher creates an order and assigns a transport; a driver (even with no
signal at loading) records statuses and documents; documents flow through
review; the transport closes with a complete, auditable file. Paper is out of
the loop for pilot drivers. No invoice is produced yet - data is MVP2-ready.
