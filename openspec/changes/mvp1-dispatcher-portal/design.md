# Design: MVP1 dispatcher portal & localization

- Portal: Vite + React + TS, TanStack Router + Query, Tailwind + shadcn/ui;
  typed API client from `packages/shared` (openapi-typescript).
- Dashboard query groups transports by state per selected groups (server
  scoped); attention indicator = incomplete documents or rejected review.
- Forms reuse server validation errors; order edit fields disabled from
  server-provided `editable` flag (reserved for MVP2 invoice link).
- Company-admin area routes guarded by role claim; user/group/truck tables
  against admin endpoints.
- i18n: `react-i18next`, per-app catalogs `cs/en/de`; initial language from
  profile after login (PATCH /auth/me on switch); fallback `en` (portal) /
  `cs` (PWA); no hardcoded UI strings.
