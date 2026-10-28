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
Supported currencies are CZK and EUR; an order created without a currency
gets the default currency from portal settings.

#### Scenario: Create order
- **WHEN** a dispatcher saves a new order with all required fields
- **THEN** the system stores it with a unique identifier within the selected
  group and it becomes available for driver assignment

#### Scenario: Missing billing data
- **WHEN** an order is submitted without unit price or VAT information
- **THEN** the system rejects it and reports the missing fields

#### Scenario: Default currency applied
- **WHEN** a dispatcher creates an order without specifying a currency
- **THEN** the system stores the order with the default currency from portal
  settings

#### Scenario: Unsupported currency rejected
- **WHEN** an order is submitted with a currency other than CZK or EUR
- **THEN** the system rejects it and reports the unsupported currency

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
A dispatcher SHALL be able to assign drivers of the transport's group to a
transport, at most two at a time; every assigned driver SHALL see the
transport in their active list and either MAY act on it. Assignments of
drivers outside the transport's group MUST be rejected, as MUST assigning a
third driver to the same transport.

#### Scenario: Assign driver
- **WHEN** a dispatcher assigns a driver of the transport's group to a
  transport
- **THEN** the transport appears in that driver's active list

#### Scenario: Second driver
- **WHEN** a dispatcher assigns a second driver to a transport that has one
- **THEN** both drivers see the transport and either can act on it

#### Scenario: Third driver rejected
- **WHEN** a dispatcher tries to assign a third driver to a transport
- **THEN** the system rejects the assignment and the pair is unchanged

#### Scenario: Foreign driver rejected
- **WHEN** a dispatcher tries to assign a driver who is not in the
  transport's group
- **THEN** the system rejects the assignment and the transport is unchanged

### Requirement: Driver switch
The dispatcher SHALL be able to add or replace an assigned driver while the
transport is in any state; the system MUST record the change in the event log
and MUST update both drivers' active lists accordingly.

#### Scenario: Swap during ride
- **WHEN** a transport is in-transit and the dispatcher replaces driver A
  with driver B
- **THEN** driver B sees the transport as active, driver A no longer does,
  and an event records the change

### Requirement: Multiple transports per order
A dispatcher SHALL be able to create more than one transport on a single
order when the goods must be split across vehicles; each transport MUST have
its own state machine and event history, and billing data MUST stay on the
order.

#### Scenario: Split order
- **WHEN** a dispatcher creates a second transport on an order that already
  has one
- **THEN** both transports exist under the order and a transition on one
  leaves the other unchanged

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
