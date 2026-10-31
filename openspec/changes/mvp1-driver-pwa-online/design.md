# Design: MVP1 driver PWA (online)

- Vite + React + TS + `vite-plugin-pwa` (manifest, service worker for app
  shell caching only - no data caching yet).
- **API types codegen (prerequisite, first consumer is this app):** fetch
  `/api/openapi.json` from the running API (served when debug) and generate
  `packages/shared` types with openapi-typescript behind a `make` target;
  both frontends depend on `@karolina/shared` and never hand-write API model
  types. `mvp1-dispatcher-portal` reuses this pipeline.
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
- **Platform readiness (Android + iOS):** iOS has no install prompt - in-app
  install help screens (Android: `beforeinstallprompt` button; iOS: "Share ->
  Add to Home Screen" steps). Standalone layout uses `dvh` units and
  safe-area insets (notch/home indicator). Camera capture via
  `<input capture>` (opens the camera app on both platforms). Service worker
  stays shell-cache only (requires iOS 16.4+ for SW in standalone; MVP1
  features do not depend on the SW).

## Screen flow (locked - the app has no more screens than these)

```
login --> tasks [ Active | History ]
                | one card per active transport (unseen = highlighted,
                v  badge on the tab)
        transport card/detail
        +-------------------------------+
        | cargo    Aretesy -> Zastavka  |
        |                               |
        | [  BIG PRIMARY BUTTON      ]  <-- next legal driver transition
        |                               |     (from the server state machine:
        | [ + PRIDAT DOKLAD          ]  <-- capture flow; no client-side
        +-------------------------------+     state logic beyond "next action")
                |
                v
        capture: pick type --> <input capture> --> presigned PUT --> confirm
                --> "submitted" (state pending-review)

        history --> read-only detail + documents (versions, review state)
        install help --> Android auto-prompt / iOS "Add to Home Screen" steps
```

- Exactly 5 routes: login, tasks, transport detail (also serves capture),
  history detail, install help. Anything beyond these is scope drift unless a
  new OpenSpec change says so.
- `mvp1-offline-sync` inherits this map: tasks, transport detail and capture
  are the screens that must keep working offline.
