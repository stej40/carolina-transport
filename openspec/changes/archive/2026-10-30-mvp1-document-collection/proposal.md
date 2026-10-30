# Proposal: MVP1 document collection

## Why
Each transport produces paperwork (weighbridge tickets for loading/unloading,
hull-cleaning certificate, transport order...). Replacing the office sorting
job means capturing these digitally, running them through dispatcher review,
and knowing exactly when a transport file is complete.

## What Changes
- New capability `document-collection`: data-driven document taxonomy (types +
  required attributes from discovery), presigned direct-to-Garage uploads by
  driver or dispatcher - dispatchers may upload on a driver's behalf during an
  active transport (bytes never transit the API), approve/reject-with-reason
  loop, versioned
  resubmissions kept for audit, per-transport completeness check exposed to
  both roles.

## Out of scope
Offline capture/queue (mvp1-offline-sync), OCR extraction (MVP3 - `data` JSONB
stays free-form and OCR-ready by design), invoice generation (MVP2).

## Follow-ups (MVP1 accepted limits - improve later)
- The per-transport required-document set is computed from fixed rules only
  (CMR => `is_international`, weighbridge pair => weight-priced order unit).
  `cleaning_declaration` and `delivery_note` have no attribute to key off, so
  they stay optional dispatcher-added documents, and discovery's "dispatcher
  can adjust the required set per transport" (§1 completeness rule) is NOT
  implemented - MVP2+ needs a required-set override table + portal UI.
- Required document attributes are entered by hand (driver or dispatcher via
  `PATCH /documents/{id}/attributes`) and approve is refused until every
  type-required field is filled. Improve with MVP3 OCR: pre-fill the
  attributes from the photo so the human only verifies/corrects them, and
  keep the approve gate checking the merged OCR + manual values.

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
