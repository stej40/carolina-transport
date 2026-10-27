# Proposal: MVP1 offline sync

## Why
Loading and unloading sites often have no signal. Drivers must still record
statuses and photograph paperwork on the spot; everything must land exactly
once when connectivity returns. This is the hardest MVP1 milestone and the
one the data model was designed for from day one (idempotency keys, event
log, client-side UUIDs).

## What Changes
- PWA gains offline-first behavior: IndexedDB (Dexie) cache + durable outbox,
  optimistic local application, sync manager with compare-and-set conflict
  guards.
- Documents can be captured offline and upload later (deferred exactly-once
  presigned upload, pending-sync state).
- MODIFIES `driver-pwa` (status recording queued offline, assignment
  notification after reconnect) and `document-collection` (deferred upload,
  offline document queue).

## Out of scope
Conflict UI beyond "server wins + notify", push notifications, native apps.

## Capabilities
### New Capabilities
(none)

### Modified Capabilities
- `driver-pwa` (specs/driver-pwa) - offline capture, queued statuses, offline
  assignment indication
- `document-collection` (specs/document-collection) - deferred upload, offline
  document queue

## Impact
- `apps/driver-pwa` service worker + Dexie layer; relies on idempotency and
  CAS semantics already specced in transports.

**Depends on:** `mvp1-driver-pwa-online`, `mvp1-document-collection`.
