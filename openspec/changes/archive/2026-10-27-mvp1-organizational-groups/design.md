# Design: MVP1 organizational groups

Schema below is the proposal from `mvp1-domain-discovery` (must be signed off
before migration).

## Entities
- `groups` (id UUID PK, name, created_at)
- `group_members` (group_id FK, user_id FK, UNIQUE pair) - dispatcher
  memberships, many-to-many; no min/max constraint on dispatcher members per
  group (0..n)
- `trucks` (id UUID PK, spz UNIQUE, group_id FK NOT NULL)
- `trailers` (id UUID PK, spz UNIQUE, group_id FK NOT NULL) - added at
  domain-discovery sign-off (Jiří): trailer master data alongside trucks
- `users.group_id` FK nullable - home group for role `driver` (drivers belong
  to exactly one group; dispatchers have none, they use `group_members`)

## Scoping enforcement
Query dependency `scoped_groups(user)` returns the group ids a dispatcher may
touch; every domain list/detail mutation filters by it and returns
not-found for foreign rows (no existence leak). company-admin bypasses
filter, system-admin bypasses everything. Same helper guards resource-move
endpoints: source and target group must both be in caller's set unless
caller is company-admin.

## API sketch (all under /api/v1, JWT)
- POST/GET/PATCH `/groups` (company-admin create; GET per role visibility)
- PUT/DELETE `/groups/{id}/members/{user_id}` (company-admin)
- PUT `/drivers/{id}/group` and `/trucks/{id}/group`, `/trailers/{id}/group`
  (company-admin anywhere, dispatcher own-groups only; dispatcher
  cross-move between own groups = two calls or single endpoint with
  from/to check)
- POST/GET `/trucks`, `/trailers`
