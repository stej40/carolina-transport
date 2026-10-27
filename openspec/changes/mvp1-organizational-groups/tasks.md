# Tasks: MVP1 organizational groups

## Schema & models
- [ ] Alembic: `groups`, `group_members`, `trucks`, `users.group_id`
- [ ] SQLAlchemy models mirroring design.md (UUID PKs)

## API
- [ ] Group CRUD + membership management endpoints with company-admin guards
- [ ] Truck registration + assignment endpoints (dispatcher own-group rules)
- [ ] Driver group assignment endpoint
- [ ] `scoped_groups` dependency wired into all domain queries (used first by
      transports CRUD in the next change)

## Tests
- [ ] Membership matrix: dispatcher sees own groups only; foreign group
      behaves as not-found
- [ ] Dispatcher move between own groups ok; move involving foreign group 403
- [ ] company-admin any-group moves; system-admin unrestricted
