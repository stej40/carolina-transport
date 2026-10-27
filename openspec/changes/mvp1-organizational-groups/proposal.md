# Proposal: MVP1 organizational groups

## Why
Dispatchers work in crews: a group bundles drivers and trucks into a
workspace. Without group scoping every dispatcher would see (and could
disturb) the whole company's resources; group membership is also the basis
for assigning drivers to orders later.

## What Changes
- New capability `organizational-groups`: groups link dispatchers (members),
  drivers, trucks and trailers (assigned resources); orders/transports will
  belong to exactly one group (enforced by the dependent transports change).
- Company-admin manages groups and dispatcher memberships; dispatchers assign
  drivers/trucks within their own groups and move resources between their own
  groups.
- Truck and trailer master data (SPZ), no availability scheduling in MVP1.
- Group-scoped visibility on all queries: foreign groups respond as-if-absent
  for dispatchers; company-admin sees all; system-admin unrestricted.

## Out of scope
Order/transport CRUD itself (mvp1-transports-and-orders), portal UI screens
(mvp1-dispatcher-portal), truck scheduling, driver-side UI.

## Capabilities
### New Capabilities
- `organizational-groups`

### Modified Capabilities
(none - identity-auth roles already exist; group scoping is this capability's
own behavior)

## Impact
- New tables: `groups`, `group_members`, `trucks`, `trailers` (+ group
  assignment on driver users); `group_id` column arrives with orders in
  mvp1-transports-and-orders.
- Shared query-scoping dependency in `apps/api/app/deps.py`.

**Depends on:** `mvp1-domain-discovery` sign-off (domain schema gate).
