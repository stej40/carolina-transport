# document-collection (offline delta)

## MODIFIED Requirements

### Requirement: Document upload
Drivers and dispatchers SHALL attach documents to a transport by uploading
photos or PDFs directly to object storage via time-limited presigned URLs,
without the file bytes passing through the API server. Uploads MAY be sent
immediately or deferred by the driver PWA's offline queue; the presigned URL
is obtained at actual upload time.

#### Scenario: Photo upload from the field
- **WHEN** a driver requests to attach a weighbridge ticket photo
- **THEN** the system issues a presigned upload URL and, after upload, the
  document appears attached to the transport in state pending-review

#### Scenario: Expired URL
- **WHEN** a client tries to use a presigned URL after its expiry
- **THEN** storage rejects the upload and the system can issue a fresh URL

## ADDED Requirements

### Requirement: Offline document queue
A document captured without connectivity SHALL stay pending-sync on the
device until its upload completes; deferred uploads MUST be exactly-once
(idempotency-keyed) and the document becomes visible to the dispatcher only
after successful upload.

#### Scenario: Capture without signal
- **WHEN** a driver photographs a weighbridge ticket with no connectivity
- **THEN** the photo is queued on the device with its type and metadata and
  shows as pending-sync to the driver

#### Scenario: Deferred upload on reconnect
- **WHEN** the device regains connectivity and the queue drains
- **THEN** the document uploads exactly once, moves to pending-review and
  appears in the dispatcher's review view

#### Scenario: Retried upload deduplicated
- **WHEN** an upload attempt fails mid-way and is retried with the same
  idempotency key
- **THEN** the system keeps a single document; no duplicate enters review

#### Scenario: Pending-sync does not satisfy completeness
- **WHEN** a transport is checked while a required document is still queued
  on the driver's device
- **THEN** the document does not count and the transport stays incomplete
