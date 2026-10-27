# Proposal: MVP1 dispatcher portal & localization

## Why
Dispatchers need the desktop workspace (dashboard, order forms, review) and
admins need the group/user management screens. Both apps must also speak each
user's language (cs/en/de), driven by the profile setting shipped with auth.

## What Changes
- New capability `dispatcher-portal`: group-scoped dashboard by transport
  state with attention indicators, order create/edit forms (billing fields +
  server editability), driver assignment (same group), document review, group
  resource management, company-admin area.
- New capability `ui-localization`: react-i18next in both frontends, profile
  preference applied, English fallback (portal) / Czech fallback (PWA),
  language switcher persists to profile.

## Out of scope
API endpoints (delivered by the domain changes this depends on), driver UX
(mvp1-driver-pwa-online), push notifications.

## Capabilities
### New Capabilities
- `dispatcher-portal`
- `ui-localization`

### Modified Capabilities
(none)

## Impact
- `apps/dispatcher-web` grows from scaffold; `apps/driver-pwa` gains i18n
  wiring only; generated API types in `packages/shared` consumed via TanStack
  Query.

**Depends on:** `mvp1-organizational-groups`, `mvp1-transports-and-orders`,
`mvp1-document-collection` (APIs), `mvp1-driver-pwa-online` (for PWA i18n).
