# Spec Delta

## MODIFIED Requirements

### Requirement: Truck master data
The system SHALL maintain trucks as named entities identified by registration
mark (SPZ), each belonging to at most one group and retire-able per "Fleet
retirement". Truck availability scheduling is not enforced in MVP1.

#### Scenario: Register truck
- **WHEN** an authorized user records a new truck with its registration mark
- **THEN** the truck becomes assignable to groups

#### Scenario: No scheduling conflict check
- **WHEN** the same truck is used on two transports with overlapping dates
- **THEN** the system stores both without rejecting either

### Requirement: Trailer master data
The system SHALL maintain trailers as named entities identified by
registration mark (SPZ), each belonging to at most one group and retire-able
per "Fleet retirement". Trailer availability scheduling is not enforced in
MVP1.

#### Scenario: Register trailer
- **WHEN** an authorized user records a new trailer with its registration mark
- **THEN** the trailer becomes assignable to groups

#### Scenario: Trailer SPZ uniqueness
- **WHEN** an authorized user records a trailer with an SPZ already in use
- **THEN** the system rejects the registration

## ADDED Requirements

### Requirement: Fleet registration restricted to administrators
A truck or trailer SHALL be registerable only by a company-admin or a
system-admin. A dispatcher attempting to register fleet MUST receive an
authorization error and no record MUST be created. Existing fleet records and
the dispatcher's ability to move vehicles between their own groups are
unaffected.

#### Scenario: Dispatcher cannot register a truck
- **WHEN** a dispatcher submits a new truck registration
- **THEN** the system rejects the request and no truck exists

#### Scenario: Company-admin registers a truck
- **WHEN** a company-admin registers a new truck with a free SPZ in one of the
  company's groups
- **THEN** the truck is created and visible to that group's dispatchers

### Requirement: Fleet retirement
A company-admin or system-admin SHALL be able to silently retire (soft
delete) and later restore trucks and trailers. A retired vehicle keeps its
row, is hidden from listings and dispatcher views, and MUST NOT be attachable
to new transports; transport history referencing it stays intact. SPZ
uniqueness applies to active vehicles only: retiring frees the SPZ for
re-registration, and restoring fails with a conflict while the SPZ is taken.

#### Scenario: Retire hides the vehicle
- **WHEN** a company-admin retires a truck
- **THEN** the truck no longer appears in dispatcher or default listings and
  the action leaves no visible notification

#### Scenario: History preserved
- **WHEN** a transport that used a retired truck is listed afterwards
- **THEN** the transport still shows its truck's registration mark

#### Scenario: Retired vehicle rejected on new transport
- **WHEN** a transport is created or updated with a retired truck or trailer
- **THEN** the system rejects the reference and the transport is unchanged

#### Scenario: SPZ freed for re-registration
- **WHEN** an admin registers a vehicle with the SPZ of a retired one
- **THEN** registration succeeds while the retired row remains retired

#### Scenario: Restore when SPZ free
- **WHEN** an admin restores a retired vehicle whose SPZ is not in active use
- **THEN** the vehicle becomes visible and assignable again

#### Scenario: Restore conflict
- **WHEN** an admin restores a retired vehicle whose SPZ has been re-registered
- **THEN** the system responds with a conflict error and nothing changes

### Requirement: Fleet unassignment
A company-admin or system-admin SHALL be able to remove a truck or trailer
from its group, leaving it unassigned. Unassigned vehicles SHALL be visible
and manageable by admins only; dispatchers MUST NOT see or address them. An
admin SHALL be able to assign an unassigned vehicle to any group using the
existing group-move operation.

#### Scenario: Admin unassigns truck
- **WHEN** a company-admin removes a truck from group G
- **THEN** the truck appears as unassigned to admins and vanishes from the
  views of G's dispatchers

#### Scenario: Dispatcher cannot unassign
- **WHEN** a dispatcher calls the remove-from-group action
- **THEN** the system rejects the request and the assignment is unchanged

#### Scenario: Admin reassigns unassigned vehicle
- **WHEN** a system-admin moves an unassigned trailer into group H
- **THEN** the trailer is listed in group H and visible to its dispatchers

### Requirement: Fleet label editing
A dispatcher SHALL be able to update the free-text label of any active truck
or trailer in their groups; an administrator SHALL be able to do so for any
active vehicle they can address. Retired and out-of-scope vehicles MUST NOT be
addressable for label editing and the vehicle row is otherwise unchanged.

#### Scenario: Dispatcher relabels own-group truck
- **WHEN** a dispatcher of group G patches the label of a truck in G
- **THEN** the truck is returned with the new label

#### Scenario: Label edit of a hidden vehicle
- **WHEN** a label patch targets a retired truck, or a vehicle outside the
  dispatcher's groups
- **THEN** the system responds not-found and the label is unchanged
