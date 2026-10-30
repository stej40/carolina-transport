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
without the file bytes passing through the API server.

#### Scenario: Photo upload from the field
- **WHEN** a driver requests to attach a weighbridge ticket photo
- **THEN** the system issues a presigned upload URL and, after upload, the
  document appears attached to the transport in state pending-review

#### Scenario: Dispatcher uploads on driver's behalf
- **WHEN** a dispatcher attaches a document to a transport that is
  in-transit (e.g. the driver will not photograph it)
- **THEN** the system issues the same presigned upload flow and records the
  dispatcher as the uploader

#### Scenario: Expired URL
- **WHEN** a client tries to use a presigned URL after its expiry
- **THEN** storage rejects the upload and the system can issue a fresh URL

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
