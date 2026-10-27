# Design: MVP1 offline sync

- **Local store**: Dexie tables mirroring driver-relevant server state
  (transports, statuses, document drafts incl. photo blobs).
- **Outbox**: every mutation (status event, document creation, upload) is
  written locally + appended to a durable outbox with client UUID and
  Idempotency-Key; UI reads local state only.
- **Sync manager**: on connectivity/`show` event, drains outbox in order;
  429/5xx retry with backoff; permanent conflicts (CAS mismatch) stop that
  item, re-fetch server state, mark item for user attention.
- **CAS**: status transitions send expected current state; server rejects
  stale ones (from mvp1-transports-and-orders).
- **Deferred presign**: document rows hold the blob locally; presigned URL is
  requested only when the upload actually runs, avoiding expiry.
- **Testing**: Playwright with network cut (airplane-mode simulation) proving
  exactly-once for statuses and documents.
