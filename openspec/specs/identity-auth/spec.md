# identity-auth Specification

## Purpose
Authenticate system users (dispatchers and drivers) and enforce role-based
access to all API endpoints and UI areas.

## Requirements

### Requirement: User credentials sign-in
The system SHALL authenticate users with an e-mail/username and password and
issue an access token plus a refresh token on success.

#### Scenario: Valid credentials
- **WHEN** a user submits valid credentials
- **THEN** the system returns an access token and a refresh token and records
  the sign-in

#### Scenario: Invalid credentials
- **WHEN** a user submits unknown e-mail or wrong password
- **THEN** the system rejects the request with a generic error that does not
  reveal whether the account exists

### Requirement: Session refresh
The system SHALL allow obtaining a new access token using a valid refresh
token, without re-entering credentials.

#### Scenario: Refresh with valid token
- **WHEN** a client exchanges an unexpired refresh token
- **THEN** the system issues a new access token

#### Scenario: Refresh with revoked token
- **WHEN** a client presents a revoked or malformed refresh token
- **THEN** the system rejects the request and the session cannot be resumed

### Requirement: Role-based access
The system SHALL assign each user one or more roles from `driver`,
`dispatcher`, `company-admin`, `system-admin` and MUST reject any operation
not permitted for the caller's roles. Visibility: a driver sees their own
transports; a dispatcher sees only their groups (organizational-groups); a
company-admin sees all groups, orders, drivers and dispatchers; a
system-admin has unrestricted access.

#### Scenario: Driver touches dispatcher data
- **WHEN** a driver-role token calls a dispatcher-only endpoint
- **THEN** the system responds with an authorization error and changes nothing

#### Scenario: Dispatcher touches admin data
- **WHEN** a dispatcher-role token calls a company-admin endpoint
- **THEN** the system responds with an authorization error and changes nothing

### Requirement: User management by administrators
A company-admin and a system-admin SHALL be able to create user accounts with
role assignments and deactivate accounts; only a system-admin may create or
modify company-admin and system-admin accounts.

#### Scenario: Company-admin creates dispatcher
- **WHEN** a company-admin creates a dispatcher account
- **THEN** the account exists with the chosen roles and the user can sign in

#### Scenario: Dispatcher cannot create users
- **WHEN** a dispatcher without admin roles calls the user-management endpoint
- **THEN** the system rejects the request and no account is created

#### Scenario: Deactivated user cannot sign in
- **WHEN** a deactivated user attempts to sign in
- **THEN** authentication fails with the generic invalid-credentials error

### Requirement: Password protection
The system MUST store passwords only with a memory-hard hashing algorithm and
 SHALL require re-authentication to change a password.

#### Scenario: Password storage
- **WHEN** a user account is created or its password changed
- **THEN** only the password hash is persisted, never the plaintext

### Requirement: User language preference
The user profile SHALL carry a UI language preference with allowed values Czech
(`cs`), English (`en`), and German (`de`), changeable by the user, and MUST be
returned on the authenticated profile.

#### Scenario: User changes language
- **WHEN** an authenticated user updates their language preference to `de`
- **THEN** the profile stores it and later authenticated requests report `de`

#### Scenario: Unsupported language
- **WHEN** a user submits a language outside `cs`, `en`, `de`
- **THEN** the system rejects the change and keeps the previous value

### Requirement: Role replacement endpoint
The system SHALL expose an endpoint to replace an existing active user's role
set with a caller-supplied complete list, applying it as one idempotent write
and returning the updated user. Every supplied role MUST be one of the four
known roles; an empty list is accepted and leaves the target holding no roles
(unusable until roles are granted again). Rejecting the change MUST leave the
user's roles unchanged.

#### Scenario: Successful replacement
- **WHEN** an authorized caller replaces a driver user's roles with `driver,dispatcher`
- **THEN** the user's roles become exactly that set and the response returns the updated user

#### Scenario: Invalid role name rejected
- **WHEN** a role-replacement request contains a role outside `driver, dispatcher, company-admin, system-admin`
- **THEN** the system responds with a validation error and the user's roles are unchanged

#### Scenario: Empty list strips all roles
- **WHEN** an authorized caller replaces an eligible user's roles with an empty list
- **THEN** the user holds no roles and the account remains active

#### Scenario: Deactivated target rejected
- **WHEN** a role-replacement request targets a deactivated user
- **THEN** the system responds 404 and nothing changes

### Requirement: Role assignment authority matrix
For every role added AND every role removed by a change, the caller MUST hold
the required authority: `company-admin` and `system-admin` only by a
`system-admin`; `dispatcher` by a `system-admin` or `company-admin`; `driver`
by a `system-admin`, `company-admin` or `dispatcher`. A change touching
multiple roles is authorized only if the caller is authorized for every
touched role.

#### Scenario: Dispatcher grants driver back to a role-less member
- **WHEN** a dispatcher of group G adds the `driver` role to an active,
  role-less user whose home group is G
- **THEN** the change is applied

#### Scenario: Dispatcher cannot grant dispatcher
- **WHEN** a dispatcher's request adds or removes the `dispatcher` role
- **THEN** the system responds with an authorization error and roles are unchanged

#### Scenario: Company-admin grants dispatcher but not admin
- **WHEN** a company-admin grants `dispatcher` to a user, and in another request grants `company-admin`
- **THEN** the first change is applied and the second is rejected

#### Scenario: System-admin grants any role
- **WHEN** a system-admin grants `system-admin` to an eligible user
- **THEN** the change is applied

### Requirement: Dispatcher driver-assignment scope
A caller holding `dispatcher` without any admin role SHALL act on the `driver`
role only for users in the caller's group scope: the target's effective home
group (the request's `group_id` when supplied, else the target's current home
group) must be one of the caller's groups, and the target must not already
hold `dispatcher`, `company-admin` or `system-admin`. Admin callers are not
restricted by this rule.

#### Scenario: Dispatcher assigns driver in own group
- **WHEN** a dispatcher of group G grants `driver` to an active user whose home group is G
- **THEN** the role is granted and the user becomes assignable via the driver group endpoint

#### Scenario: Target outside caller's groups rejected
- **WHEN** a dispatcher grants `driver` to a user whose home group is not among the caller's groups and no in-scope `group_id` is supplied
- **THEN** the system rejects the request and roles are unchanged

#### Scenario: Dispatcher cannot touch a dispatcher account
- **WHEN** a dispatcher attempts any role change on a user already holding `dispatcher`
- **THEN** the system rejects the request

### Requirement: Role change escalation guards
The system MUST refuse a role change requested by a caller on their own
account, and MUST refuse any change that would leave no active user holding
`system-admin`: role replacement removing that role from the last active
holder, and deactivation of a last-active system-admin's account. Rejected
changes MUST have no partial effect.

#### Scenario: Self-demotion blocked
- **WHEN** a company-admin replaces their own roles with `dispatcher`
- **THEN** the system rejects the request and their roles are unchanged

#### Scenario: Last system-admin cannot deactivate
- **WHEN** the only active `system-admin` user calls the account-deactivation
  endpoint on their own account
- **THEN** the system responds 409 and the account stays active
