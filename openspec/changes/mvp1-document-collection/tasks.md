# Tasks: MVP1 document collection

## Schema & seed
- [ ] Alembic: `document_types`, `documents` (+version), `document_reviews`
- [ ] Seed document types from discovery taxonomy

## API
- [ ] Presigned upload flow (create row, presign, confirm) with group scoping
- [ ] Approve / reject-with-reason endpoints; resubmission versioning
- [ ] Completeness check computation + exposed on transport views
- [ ] Manual attribute entry per type's required attributes

## Tests
- [ ] e2e upload -> pending-review -> approve
- [ ] Dispatcher-side upload on in-transit transport: pending-review +
      uploader = dispatcher
- [ ] reject -> resubmit -> both versions in history
- [ ] missing-doc flow: transport incomplete until approved
