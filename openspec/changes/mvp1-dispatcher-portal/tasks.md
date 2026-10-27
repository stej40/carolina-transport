# Tasks: MVP1 dispatcher portal & localization

## Portal shell
- [ ] TanStack Router/Query + Tailwind/shadcn/ui wired, shared API types used
- [ ] Login flow against auth endpoints (incl. token refresh)

## Dispatcher features
- [ ] Dashboard grouped by transport state, scoped to own groups, group
      filter/combined view, attention indicators
- [ ] Order creation form (billing fields enforced) acting in a group
- [ ] Order edit form (fields disabled per server editability response)
- [ ] Driver assignment picker (same group); transport detail view
- [ ] Document review: view, approve, reject-with-reason
- [ ] Group resource management: assign/move drivers & trucks between own
      groups, register trucks

## Company-admin area
- [ ] Manage groups, dispatcher memberships, drivers, trucks, users
- [ ] Browse all orders and transports across groups

## Localization (both apps)
- [ ] react-i18next wiring + cs/en/de catalogs, language switcher persists to
      profile, English fallback (portal)
- [ ] PWA i18n wiring, Czech fallback

## Verification
- [ ] End-to-end test: order -> assign -> in-transit -> completed via portal
