# Tasks: MVP1 document collection

## Schema & seed
- [x] Alembic: `document_types`, `documents` (+version), `document_reviews`
- [x] Seed document types from discovery taxonomy

## API
- [x] Presigned upload flow (create row, presign, confirm) with group scoping
- [x] Approve / reject-with-reason endpoints; resubmission versioning
- [x] Completeness check computation + exposed on transport views
- [x] Manual attribute entry per type's required attributes

## Tests
- [x] e2e upload -> pending-review -> approve
- [x] Driver upload to unassigned transport rejected (no draft row, no
      presigned URL)
- [x] Dispatcher-side upload on in-transit transport: pending-review +
      uploader = dispatcher
- [x] reject -> resubmit -> both versions in history
- [x] missing-doc flow: transport incomplete until approved
