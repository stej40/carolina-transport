# document-collection

## Purpose
Collect the paperwork every transport requires (transport order, weighbridge
tickets for loading and unloading, hull-cleaning certificate, ...) as digital
documents, and run them through review until the transport file is complete.

## ADDED Requirements

### Requirement: Data-driven document taxonomy
The system SHALL define document types as data, each with its required
attributes, so new paperwork kinds can be added without code changes. The
concrete types are confirmed from real paperwork samples during discovery.

#### Scenario: New document type
- **WHEN** an administrator adds a document type with its required attributes
- **THEN** that type becomes selectable for new transports immediately

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

### Requirement: Review workflow
A dispatcher SHALL be able to approve or reject each submitted document;
rejection MUST carry a reason and the related transport MUST show the document
as missing/incorrect until a corrected document is approved.

#### Scenario: Reject and request correction
- **WHEN** a dispatcher rejects a blurry weighbridge photo with a reason
- **THEN** the driver sees the correction request and can resubmit

### Requirement: Completeness check
The system SHALL evaluate, per transport, whether all documents required by
its document types are present and approved, and MUST expose that status to
both dispatchers and drivers.

#### Scenario: Blocking completion
- **WHEN** a transport is marked completed while a required document is
  missing or rejected
- **THEN** the transport is flagged incomplete and cannot pass the final
  review gate

### Requirement: Document auditability
Every document version, its uploader, timestamps, and review decisions MUST
remain retrievable; superseded versions are kept, not overwritten.

#### Scenario: Resubmission history
- **WHEN** a rejected document is resubmitted and approved
- **THEN** both the rejected and approved versions are visible in history
