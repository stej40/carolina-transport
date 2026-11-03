# Proposal: Bootstrap system-admin account

## Why

Every endpoint that can create groups, users or fleet requires a
company-admin/system-admin, but the API has no account-creation endpoint
before such an account exists: a fresh deployment (pilot, `make infra-full`,
VPS) is unusable until someone runs the CLI seed script by hand. Jiří needs a
non-functional guarantee that the API always has at least one usable
system-admin - checked at startup and self-healing when not.

## What Changes

- At API startup, the system verifies that at least one **active user with the
  `system-admin` role** exists. If none does, it creates (or re-activates and
  promotes) the bootstrap account so the API is immediately usable.
- New settings `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` with
  obviously-dev placeholder defaults for the local profile.
- Prod profile guard (extending the existing fail-fast config validation):
  startup configuration is rejected if the bootstrap password is still the dev
  placeholder or shorter than the agreed minimum, matching the SECRET_KEY rule.
- No endpoint changes, no token changes: the bootstrap account is a normal
  user row and logs in through the existing `/api/v1/auth/login`.

Out of scope: forcing a password change on first login, password rotation or
expiry, continuous (non-startup) enforcement or background timers, removal of
the CLI `seed_users.py` script, UI screens for bootstrap, e-mail delivery of
generated credentials, SSO/2FA, retroactive audit of who demoted admins.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `identity-auth`: ADDED requirement "System-admin bootstrap at startup" -
  startup guarantee of at least one active system-admin, bootstrap account
  creation/re-activation semantics, configuration of bootstrap credentials,
  and refusal of dev-placeholder bootstrap credentials in the prod profile.

## Impact

- `apps/api/app/config.py`: two new settings + extension of the prod
  validator (`_prod_safety`).
- `apps/api/app/main.py`: lifespan hook calling a new bootstrap routine after
  the existing idempotency purge.
- New module `apps/api/app/bootstrap.py` (startup guard routine; reuses
  `app.security.hash_password`, `app.models.User`).
- `.env.example` / `.env.local` docs: bootstrap variables listed.
- Tests: config-validator tests (`test_runtime_configuration.py`) and a new
  startup-bootstrap test unit (lifespan is not exercised by httpx ASGITransport,
  so the routine is tested directly against the test session).
- Deployment: zero manual steps for a fresh pilot database - one known dev
  account exists in local; in prod the operator sets the password.
