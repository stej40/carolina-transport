# dispatcher-portal

## Purpose
Give dispatchers a desktop web portal to manage orders and transports, assign
drivers, and review driver-submitted documents; give company-admins an
administration area for groups, members, trucks and users.

## ADDED Requirements

### Requirement: Status dashboard
The portal SHALL show a dispatcher the transports of their own groups grouped
by state, so they see at a glance what is assigned, in transit, completed,
and blocked by missing or rejected documents. A dispatcher member of several
groups SHALL be able to filter by group or view all their groups together.

#### Scenario: Incomplete transports visible
- **WHEN** a transport has a missing or rejected required document
- **THEN** it appears in the dashboard with an attention indicator

#### Scenario: Multi-group dispatcher
- **WHEN** a dispatcher belonging to two groups opens the dashboard
- **THEN** only transports of those two groups are listed and the group can
  be selected or combined

### Requirement: Order entry
A dispatcher SHALL create transport orders acting in one of their groups,
through a form that enforces the billing-ready fields required by the
transport-lifecycle spec.

#### Scenario: Create and assign
- **WHEN** a dispatcher saves an order in their group and assigns a driver of
  the same group
- **THEN** the transport appears in the dashboard and on the driver's device

### Requirement: Document review
The portal SHALL let a dispatcher open a transport, view each attached
document (including manual data entry when OCR is unavailable), and approve or
reject it with a reason.

#### Scenario: Review queue
- **WHEN** a driver submits a document
- **THEN** it becomes visible in the transport's review view without a page
  reload requirement beyond normal refresh

### Requirement: Group resource management
The portal SHALL let a dispatcher manage resources of their own groups:
assign drivers and trucks to their groups, move them between groups they are
a member of, and register new trucks for their groups, as bounded by the
organizational-groups spec.

#### Scenario: Assign driver to group
- **WHEN** a dispatcher assigns a driver to one of their own groups
- **THEN** the driver appears in that group's resources and in the driver
  picker for orders in the group

#### Scenario: Foreign groups hidden
- **WHEN** a dispatcher opens the move-resource dialog
- **THEN** only their own groups are offered as source or destination

### Requirement: Company-admin area
The portal SHALL provide a company-admin area to manage groups (create,
rename, assign dispatchers), assign drivers and trucks to groups, manage
trucks, and browse all orders and transports across groups.

#### Scenario: Create group and assign dispatcher
- **WHEN** a company-admin creates a group and adds a dispatcher as member
- **THEN** the group immediately appears in that dispatcher's portal

#### Scenario: Dispatcher denied
- **WHEN** a dispatcher (without company-admin role) opens an admin function
- **THEN** the portal offers no admin entry points and the API rejects the
  calls

