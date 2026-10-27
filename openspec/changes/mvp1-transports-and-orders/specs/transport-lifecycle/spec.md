# transport-lifecycle

## Purpose
Manage the life of a transport from dispatcher-entered order through driver
execution to completion, with an auditable history of every state change.

## ADDED Requirements

### Requirement: Order registration
A dispatcher SHALL be able to create a transport order acting within one of
their groups, describing the delivery (customer, pickup/delivery places,
cargo, dates); the data MUST be billing-ready: quantity, unit, unit price,
currency, VAT, and billing text. Every order belongs to exactly one group.

#### Scenario: Create order
- **WHEN** a dispatcher saves a new order with all required fields
- **THEN** the system stores it with a unique identifier within the selected
  group and it becomes available for driver assignment

#### Scenario: Missing billing data
- **WHEN** an order is submitted without unit price or VAT information
- **THEN** the system rejects it and reports the missing fields

### Requirement: Order editing
A dispatcher SHALL be able to edit any order field while no invoice is linked
to the order; once an invoice is linked, the system MUST reject changes to
billing fields. Every accepted edit SHALL be recorded in the event log.

#### Scenario: Edit before invoicing
- **WHEN** a dispatcher updates the unit price of an order that has no linked
  invoice
- **THEN** the order is updated and the change is appended to the event log

#### Scenario: Edit after invoicing
- **WHEN** a dispatcher changes a billing field on an order that already has a
  linked invoice
- **THEN** the system rejects the change and the order is unchanged

### Requirement: Driver assignment
A dispatcher SHALL be able to assign a driver of the same group to an order;
the driver SHALL be able to see the assignment as their current transport.
Assignment of drivers outside the order's group MUST be rejected.

#### Scenario: Assign driver
- **WHEN** a dispatcher assigns a driver of their group to an order
- **THEN** the transport appears in that driver's active list

#### Scenario: Foreign driver rejected
- **WHEN** a dispatcher tries to assign a driver who is not in the order's
  group
- **THEN** the system rejects the assignment and the order is unchanged

### Requirement: Transport state machine
The system SHALL track each transport through the defined states (at least:
assigned, in-transit, completed) and MUST reject transitions not allowed by
the state machine. The concrete machine is finalized in discovery and then
binding.

#### Scenario: Valid transition
- **WHEN** a driver marks an assigned transport as started
- **THEN** the transport enters the in-transit state

#### Scenario: Invalid transition
- **WHEN** a client attempts a transition the state machine forbids (for
  example, reopening a completed transport)
- **THEN** the system rejects the request and the state is unchanged

### Requirement: Immutable event log
The system SHALL record every state transition and material change to a
transport as an append-only event with actor, timestamp, and previous/new
state; events MUST never be modified or deleted.

#### Scenario: Audit trail
- **WHEN** a transport's status changes
- **THEN** an event row is appended and the transport's history shows it in
  order

### Requirement: Idempotent writes
All transport write endpoints MUST accept an idempotency key and guarantee
that replaying the same request has no additional effect.

#### Scenario: Replayed request
- **WHEN** the same write with the same idempotency key is received twice
- **THEN** the second call returns the original result and creates no
  duplicate
