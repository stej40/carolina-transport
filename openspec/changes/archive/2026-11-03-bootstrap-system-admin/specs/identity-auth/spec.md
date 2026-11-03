# Spec Delta

## ADDED Requirements

### Requirement: System-admin bootstrap at startup
On startup the API SHALL ensure that at least one active user with the
system-admin role exists. When none exists, the system SHALL create the
bootstrap account from configuration, or re-activate it and restore its
system-admin role when a user with the bootstrap e-mail already exists. When
at least one active system-admin exists, startup SHALL change no user. The
bootstrap password MUST NOT be written to logs.

#### Scenario: Fresh database becomes usable
- **WHEN** the API starts against a database with no active system-admin
- **THEN** a user with the configured bootstrap e-mail exists, is active,
  holds the system-admin role and can sign in with the configured password

#### Scenario: Bootstrap account revived after lock-out
- **WHEN** the bootstrap account was disabled or demoted and no other active
  system-admin exists, and the API restarts
- **THEN** the bootstrap account is active again with the system-admin role
  and its password is reset to the configured value

#### Scenario: Existing administrators untouched
- **WHEN** the API starts while at least one active system-admin exists
- **THEN** no account is created, disabled or promoted, and no password is
  changed

### Requirement: Bootstrap credentials come from configuration
The bootstrap account's e-mail and password SHALL be read from configuration
(`BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD`). The local profile SHALL
provide obviously-development placeholder defaults; the production profile
MUST fail fast at startup when the bootstrap password is still the dev
placeholder or shorter than the minimum configured password length.

#### Scenario: Local profile starts with placeholder credentials
- **WHEN** the API runs in the local profile without bootstrap variables set
- **THEN** startup succeeds and the bootstrap account uses the documented dev
  placeholder e-mail and password

#### Scenario: Production rejects placeholder password
- **WHEN** the prod profile is active and `BOOTSTRAP_ADMIN_PASSWORD` equals
  the dev placeholder
- **THEN** the application refuses to start with a configuration error

#### Scenario: Production rejects weak password
- **WHEN** the prod profile is active and `BOOTSTRAP_ADMIN_PASSWORD` is empty
  or shorter than the minimum length
- **THEN** the application refuses to start with a configuration error
