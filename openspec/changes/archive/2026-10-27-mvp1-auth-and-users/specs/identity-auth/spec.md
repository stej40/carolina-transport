# identity-auth

## Purpose
Authenticate system users (dispatchers and drivers) and enforce role-based
access to all API endpoints and UI areas.

## ADDED Requirements

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
