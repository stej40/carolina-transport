# driver-pwa

## Purpose
Give drivers an installable mobile PWA to see their transports, record status
changes, and photograph paperwork. Offline-first operation is added by the
later mvp1-offline-sync change.

## ADDED Requirements

### Requirement: Driver task view
The PWA SHALL show the signed-in driver only their own active transports and
their transport history, with state, route places, and what is expected next.

#### Scenario: New assignment appears
- **WHEN** a dispatcher assigns a transport while the driver is online
- **THEN** it appears in the driver's active list

#### Scenario: Completed transports remain reachable
- **WHEN** a transport of the driver is completed
- **THEN** it moves to the driver's history and stays readable with its
  documents

### Requirement: Assignment notification
The PWA SHALL indicate in-app when a new transport has been assigned to the
driver (unread badge plus highlighted entry after sync). OS-level push
notifications are out of MVP1 scope; the transport event log remains the
reserved trigger for a future push integration.

#### Scenario: New assignment while app open
- **WHEN** a dispatcher assigns a transport and the driver's PWA syncs
- **THEN** the badge increases and the new transport is highlighted until
  acknowledged

### Requirement: Status recording
The driver SHALL be able to mark key transport states (start, arrival at
pickup, arrival at delivery, completed) from the phone.

#### Scenario: Start transport
- **WHEN** the driver taps start on an assigned transport
- **THEN** the state change is submitted and reflected to the dispatcher

### Requirement: Simple field UX
The driver interface MUST be operable with large touch targets and minimal
text input, and MUST be installable from the browser without an app store.

#### Scenario: Install on phone
- **WHEN** a driver opens the portal URL on their phone and chooses "install"
- **THEN** the PWA is added to the home screen and launches standalone
