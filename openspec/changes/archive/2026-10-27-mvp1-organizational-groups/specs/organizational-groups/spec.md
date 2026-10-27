# organizational-groups

## Purpose
Organize dispatchers, drivers, trucks and trailers into groups that act as
dispatcher workspaces, so that orders, transports and fleet resources live
within a clearly scoped boundary and cross-group visibility is reserved for
company and system administrators.

## ADDED Requirements

### Requirement: Group as workspace
The system SHALL provide groups as a logical layer linking dispatchers (as
members), drivers and trucks (as assigned resources). Every order and
transport MUST belong to exactly one group.

#### Scenario: Order created inside a group
- **WHEN** a dispatcher creates an order while acting in one of their groups
- **THEN** the order and its transports belong to that group

### Requirement: Group membership management
The company-admin SHALL create groups and assign dispatchers to them; a
dispatcher may be member of one or more groups and can work only in groups
they are a member of. A group MAY have any number of dispatcher members,
including none.

#### Scenario: Dispatcher added to group
- **WHEN** a company-admin assigns a dispatcher to a group
- **THEN** the group appears as a workspace in that dispatcher's portal

#### Scenario: Dispatcher in several groups
- **WHEN** a company-admin assigns a dispatcher who already has a group to a
  second group
- **THEN** both groups appear as workspaces in that dispatcher's portal

#### Scenario: Group with several dispatchers
- **WHEN** a company-admin assigns a second dispatcher to a group that
  already has one
- **THEN** both dispatchers see that group as a workspace

#### Scenario: Group without dispatchers
- **WHEN** a company-admin creates a group with no dispatcher members
- **THEN** the group exists and drivers/trucks can be assigned to it, and it
  is visible only to company-admin (no dispatcher portal shows it)

#### Scenario: Dispatcher without membership
- **WHEN** a dispatcher tries to act in a group they are not a member of
- **THEN** the system rejects the action and the group is not visible to them

### Requirement: Resource assignment to groups
Drivers, trucks and trailers SHALL be assignable to a group by the
company-admin (any group) or by a dispatcher (their own groups only). A
dispatcher SHALL be able to move a driver, truck or trailer between two
groups they are a member of; moving resources involving a foreign group is
company-admin work. A driver, truck or trailer is visible in dispatcher views
only within its group.

#### Scenario: Dispatcher adds a truck to their group
- **WHEN** a dispatcher assigns an existing truck to one of their own groups
- **THEN** the truck is listed among that group's resources

#### Scenario: Dispatcher moves driver between own groups
- **WHEN** a dispatcher moves a driver from one of their groups to another of
  their groups
- **THEN** the driver leaves the source group and appears in the target group

#### Scenario: Move involving foreign group denied
- **WHEN** a dispatcher tries to move a resource to or from a group they are
  not a member of
- **THEN** the system rejects the move and the assignment is unchanged

#### Scenario: Driver moved between groups by company-admin
- **WHEN** a company-admin reassigns a driver to another group
- **THEN** the driver no longer appears in the previous group and appears in
  the new group

### Requirement: Truck master data
The system SHALL maintain trucks as named entities identified by registration
mark (SPZ), each belonging to one group. Truck availability scheduling is not
enforced in MVP1.

#### Scenario: Register truck
- **WHEN** an authorized user records a new truck with its registration mark
- **THEN** the truck becomes assignable to groups

#### Scenario: No scheduling conflict check
- **WHEN** the same truck is used on two transports with overlapping dates
- **THEN** the system stores both without rejecting either

### Requirement: Trailer master data
The system SHALL maintain trailers as named entities identified by
registration mark (SPZ), each belonging to one group. Trailer availability
scheduling is not enforced in MVP1.

#### Scenario: Register trailer
- **WHEN** an authorized user records a new trailer with its registration mark
- **THEN** the trailer becomes assignable to groups

#### Scenario: Trailer SPZ uniqueness
- **WHEN** an authorized user records a trailer with an SPZ already in use
- **THEN** the system rejects the registration

### Requirement: Group-scoped visibility
The system SHALL limit a dispatcher's access to groups they are a member of;
orders, transports, drivers, trucks, trailers and resources of other groups
MUST NOT be visible or addressable through their session.

#### Scenario: Cross-group read denied
- **WHEN** a dispatcher requests an order belonging to a group they are not a
  member of
- **THEN** the system responds as if the order did not exist

### Requirement: Company-wide and system-wide visibility
A company-admin SHALL see all groups with their orders, transports, drivers,
trucks, trailers and dispatchers. A system-admin SHALL have unrestricted
access to all data and administration functions.

#### Scenario: Company-admin oversight
- **WHEN** a company-admin opens the groups overview
- **THEN** every group is listed with its orders, members and resources

#### Scenario: System-admin full access
- **WHEN** a system-admin calls any endpoint
- **THEN** access is granted regardless of group membership
