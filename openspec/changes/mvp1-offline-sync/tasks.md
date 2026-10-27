# Tasks: MVP1 offline sync

## Storage & outbox
- [ ] Dexie schema: transports cache, status queue, document drafts (blob
      store), outbox with idempotency keys
- [ ] Optimistic local apply on all driver mutations

## Sync manager
- [ ] Drain loop with backoff; compare-and-set conflict guards; conflict ->
      refetch + surface to driver
- [ ] Deferred presigned upload (URL fetched at upload time) with exactly-once
      retry
- [ ] Pending-sync indicators in UI (statuses + documents); completeness
      excludes pending-sync documents (server behavior, verify)

## Verification
- [ ] Airplane-mode Playwright test: statuses + photo captured offline, app
      restarted, reconnect -> everything synced exactly once
- [ ] Manual test on a real phone without signal at a site
