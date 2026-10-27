# Proposal: MVP1 document collection

## Why
Each transport produces paperwork (weighbridge tickets for loading/unloading,
hull-cleaning certificate, transport order...). Replacing the office sorting
job means capturing these digitally, running them through dispatcher review,
and knowing exactly when a transport file is complete.

## What Changes
- New capability `document-collection`: data-driven document taxonomy (types +
  required attributes from discovery), presigned direct-to-Garage uploads
  (bytes never transit the API), approve/reject-with-reason loop, versioned
  resubmissions kept for audit, per-transport completeness check exposed to
  both roles.

## Out of scope
Offline capture/queue (mvp1-offline-sync), OCR extraction (MVP3 - `data` JSONB
stays free-form and OCR-ready by design), invoice generation (MVP2).

## Capabilities
### New Capabilities
- `document-collection`

### Modified Capabilities
(none)

## Impact
- Tables `document_types`, `documents`, `document_reviews`; S3 presign
  endpoints (boto3 path already proven by `scripts/smoke_s3.py`).

**Depends on:** discovery sign-off, `mvp1-transports-and-orders` (documents
attach to transports).
