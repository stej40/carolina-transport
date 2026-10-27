# Proposal: MVP1 driver PWA (online)

## Why
Drivers are the data source: statuses and photos of paperwork must be
captured at the site, on the phone, without IT literacy barriers. The PWA is
installable (no app store) and online-first here; offline is the follow-up
change.

## What Changes
- New capability `driver-pwa` (online part): login, own active transports +
  history, in-app assignment notification (badge + highlight; push reserved
  via event log for later), status actions posting transitions, camera capture
  -> direct presigned upload, giant-button field UX.

## Out of scope
Offline queue/outbox (mvp1-offline-sync), document review UI (portal), i18n
wiring (mvp1-dispatcher-portal carries `ui-localization` for both apps), push
notifications, native apps.

## Capabilities
### New Capabilities
- `driver-pwa`

### Modified Capabilities
(none)

## Impact
- `apps/driver-pwa`: real app replacing Vite scaffold (TanStack Router/Query,
  camera capture via `capture` input, auth flow against `/api/v1/auth`).

**Depends on:** `mvp1-transports-and-orders`, `mvp1-document-collection`.
