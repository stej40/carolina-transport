# driver-pwa (offline delta)

## MODIFIED Requirements

### Requirement: Assignment notification
The PWA SHALL indicate in-app when a new transport has been assigned to the
driver (unread badge plus highlighted entry after sync). OS-level push
notifications are out of MVP1 scope; the transport event log remains the
reserved trigger for a future push integration.

#### Scenario: New assignment while app open
- **WHEN** a dispatcher assigns a transport and the driver's PWA syncs
- **THEN** the badge increases and the new transport is highlighted until
  acknowledged

#### Scenario: Assignment while offline
- **WHEN** a transport was assigned while the driver had no connectivity
- **THEN** the indication appears right after the app reconnects and syncs

### Requirement: Status recording
The driver SHALL be able to mark key transport states (start, arrival at
pickup, arrival at delivery, completed) from the phone, with or without
connectivity.

#### Scenario: Start transport online
- **WHEN** the driver taps start on an assigned transport with connectivity
- **THEN** the state change is submitted and reflected to the dispatcher

#### Scenario: Start transport offline
- **WHEN** the driver taps start with no connectivity
- **THEN** the change is queued locally, shown as pending in the UI, and
  synced exactly once when the connection returns

## ADDED Requirements

### Requirement: Offline capture
The PWA MUST let the driver record statuses and capture document photos
without connectivity, queue them locally in a durable outbox, and sync
automatically when a connection returns, without creating duplicates on
retry or loss on app restart.

#### Scenario: Airplane mode workflow
- **WHEN** a driver photographs a weighbridge ticket with no signal and later
  regains connectivity
- **THEN** the queued status events and the document upload sync successfully
  exactly once

#### Scenario: Outbox survives restart
- **WHEN** the driver closes the PWA while items are still queued
- **THEN** after reopening, the outbox drains normally on next connectivity
