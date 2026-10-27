# Design: MVP1 driver PWA (online)

- Vite + React + TS + `vite-plugin-pwa` (manifest, service worker for app
  shell caching only - no data caching yet).
- TanStack Router/Query against `/api/v1`; JWT module from mvp1-auth-and-users
  with token refresh on 401.
- Views: login, active transport card (big primary action = next state),
  history list, document capture (camera via `<input capture>` -> presigned
  upload flow from mvp1-document-collection).
- Assignment notification: polling query for unseen assignments -> unread
  badge + highlighted card until opened/acknowledged (read-state stored
  locally; server read-state not needed in MVP1).
- UX constraints: min touch target 48 px, one action per screen, no free text
  except login; Czech-first copy until i18n lands with the portal change.
