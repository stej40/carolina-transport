# Tasks: MVP1 organizational groups

## Schema & models
- [x] Alembic: `groups`, `group_members`, `trucks`, `trailers`, `users.group_id`
- [x] SQLAlchemy models mirroring design.md (UUID PKs)

## API
- [x] Group CRUD + membership management endpoints with company-admin guards
- [x] Truck + trailer registration and assignment endpoints (dispatcher
      own-group rules)
- [x] Driver group assignment endpoint
- [x] `scoped_groups` dependency wired into all domain queries (used first by
      transports CRUD in the next change)

## Tests
- [x] Membership matrix: dispatcher sees own groups only; foreign group
      behaves as not-found; group with zero and with multiple dispatchers
      accepted
- [x] Dispatcher move between own groups ok; move involving foreign group 403
- [x] company-admin any-group moves; system-admin unrestricted
