# Tasks: MVP1 deployment & pilot

## Infra
- [ ] Prod compose + Caddyfile (TLS, reverse proxy /api), secrets via env
      files; deploy.md runbook (fresh install, upgrade, restore)
- [ ] Backup jobs: nightly pg_dump + Garage mirror to second bucket; restore
      drill executed once and documented

## Operations
- [ ] Healthcheck monitoring + operator alerting wired and test-fired

## Pilot
- [ ] Onboard 2-3 drivers (install PWA, accounts seeded, first real week)
- [ ] Re-verify real-phone PWA checks (from mvp1-driver-pwa-online) on the
      deployed URL with both Android and iPhone: install, camera capture,
      field usability with real drivers
- [ ] Collect feedback, triage into new OpenSpec changes
- [ ] Verify MVP1 Definition of Done (proposal.md) with Jiří - then archive
      all MVP1 changes
