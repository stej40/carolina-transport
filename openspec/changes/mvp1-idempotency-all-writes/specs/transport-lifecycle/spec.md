# Spec Delta

## MODIFIED Requirements

### Requirement: Idempotent writes
Every write endpoint under `/api/v1` MUST require an `Idempotency-Key`
header and reject a request without one with HTTP 400. Replaying the same
request with the same key MUST return the original result with no additional
effect; the same key with a different payload MUST be rejected. Auth token
endpoints (login, refresh, logout) are exempt and their responses MUST NOT
be stored in the replay cache.

#### Scenario: Replayed request
- **WHEN** the same write with the same idempotency key is received twice
- **THEN** the second call returns the original result and creates no
  duplicate

#### Scenario: Missing key rejected
- **WHEN** a write request arrives without an `Idempotency-Key` header
- **THEN** the system rejects it with HTTP 400 and performs no change

#### Scenario: Conflicting reuse rejected
- **WHEN** a key already used is presented with a different request payload
- **THEN** the system rejects it and the original resource is unchanged

#### Scenario: Auth endpoints exempt
- **WHEN** a client logs in twice with the same credentials and no
  idempotency key
- **THEN** both calls issue fresh token pairs and nothing is written to the
  replay cache
