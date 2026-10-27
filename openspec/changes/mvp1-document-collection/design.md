# Design: MVP1 document collection

- **Taxonomy**: `document_types` (id, key, name, required_attributes JSONB
  schema-lite, active flag) seeded from discovery; transports require types
  per discovery rules.
- **Upload flow**: client requests `POST /transports/{id}/documents` -> API
  creates a draft row + returns presigned PUT (short TTL) -> client PUTs
  bytes to Garage -> confirm call verifies object exists and flips the row to
  state=pending-review (the state in which the dispatcher sees it); unconfirmed
  drafts expire. Storage key server-generated under
  `documents/{transport_id}/{document_id}/{version}`.
- **Versions**: resubmission after reject creates a new version row; prior
  versions immutable; history endpoint lists all with uploader/timestamps.
- **Review**: approve/reject (reason required) by dispatcher of the
  document's group; rejection sets transport attention flag.
- **Completeness**: computed (not stored) per transport: every required type
  has an approved current version; exposed on transport detail + list.
- **OCR-ready**: extracted attributes go to `documents.data` JSONB later
  (MVP3); manual entry fields render from required_attributes today.
