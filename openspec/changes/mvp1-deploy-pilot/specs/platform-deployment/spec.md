# platform-deployment

## Purpose
Run the whole stack on a self-hosted VPS with TLS, backups, and health
monitoring so the company's operations survive hardware and hosting changes.

## ADDED Requirements

### Requirement: Containerized stack
The system SHALL be deployable as a Docker Compose stack (PostgreSQL, Garage,
API, frontends) behind Caddy providing TLS, startable from a clean machine
with documented commands.

#### Scenario: Fresh VPS deploy
- **WHEN** the stack is deployed on a new VPS following the runbook
- **THEN** portal, PWA, and API are reachable over HTTPS and the health
  endpoint reports OK

### Requirement: Backups
The operator MUST have automated database dumps and object-storage mirroring
to a second bucket, with a documented restore procedure.

#### Scenario: Restore test
- **WHEN** the documented restore procedure is executed against a scratch
  environment
- **THEN** the data including documents is recovered

### Requirement: Health monitoring
The deployment SHALL expose a health endpoint and MUST alert the operator when
the API is unreachable or unhealthy.

#### Scenario: API down
- **WHEN** the API container stops responding
- **THEN** the monitoring raises an alert to the operator
