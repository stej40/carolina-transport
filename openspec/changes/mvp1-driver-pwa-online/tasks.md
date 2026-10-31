# Tasks: MVP1 driver PWA (online)

## App shell
- [ ] Replace scaffold: vite-plugin-pwa config (manifest, icons, install),
      router, auth flow with token refresh
- [ ] OpenAPI -> shared TS types pipeline: openapi-typescript generation into
      `packages/shared`, make target, app dependency wiring
- [ ] TanStack Query wiring against generated API types

## Features
- [ ] Active transport card with next-action state buttons
- [ ] History list (completed transports with their documents)
- [ ] Assignment badge + highlighted card, acknowledge on open
- [ ] Install help: Android `beforeinstallprompt` flow; iOS "Add to Home
      Screen" step-by-step screen
- [ ] Document capture: pick type -> camera -> presigned upload -> submitted

## UX constraints
- [ ] Giant-button layout, min touch targets, no free-text screens,
      `dvh` + safe-area insets respected (iOS standalone)
- [ ] Tested on real Android and iPhone devices (dispatcher-guided) - interim:
      Android over USB (adb reverse), iPhone over LAN HTTPS dev server with a
      device-trusted cert (e.g. mkcert) or Tailscale Serve; final
      re-verification on the deployed URL in mvp1-deploy-pilot
