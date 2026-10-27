# Proposal: MVP1 auth & users

## Why
Every other MVP1 capability depends on knowing who the caller is and what they
may see. Identity (accounts, JWT sessions, four roles, admin user management,
language preference) was designed and built as milestone M1 of the split-out
program and is implemented and tested in `apps/api`.

## What Changes
- JWT access + refresh tokens (rotation, revocation), argon2 password hashing.
- Roles `driver`, `dispatcher`, `company-admin`, `system-admin` enforced on
  every authenticated endpoint.
- Admin user management (create/deactivate accounts; only system-admin may
  manage admin accounts).
- User profile with language preference (cs/en/de) and authenticated profile
  endpoint.

## Out of scope
Group membership and resource scoping (mvp1-organizational-groups), any domain
entities, frontend login screens (mvp1-dispatcher-portal / -driver-pwa-online).

## Capabilities
### New Capabilities
- `identity-auth`: accounts, sessions, roles, admin user management, profile.

### Modified Capabilities
(none)

## Impact
- `apps/api`: `app/{db,models,schemas,security,deps}.py`,
  `app/routers/{auth,users}.py`, Alembic `0001`/`0002`, `scripts/seed_users.py`,
  tests. No further changes planned - this change records shipped behavior.
