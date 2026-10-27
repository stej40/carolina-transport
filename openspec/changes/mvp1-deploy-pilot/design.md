# Design: MVP1 deployment & pilot

Self-hosted VPS, Docker Compose: postgres:18-alpine, garage:2.4 single node
(`infra/garage.toml`), api container, static frontends served via Caddy;
Caddy terminates TLS (Let's Encrypt) and reverse-proxies `/api`.

- Backups: nightly `pg_dump` to disk + off-site copy; Garage bucket mirrored
  to second bucket (`s3 mirror`); documented restore procedure with drill.
- Monitoring: external uptime check against `/api/v1/health` + alerting to
  operator (e-mail/Telegram); container restart policies.
- Secrets via env files outside git; `.env.example` documents the shape.
- Runbook: `docs/runbook/deploy.md` (fresh install, upgrades, backup restore,
  certificate handling) - created in this change, fulfilling M8.
- Pilot: 2-3 drivers, their phones, real transports; feedback loop into
  backlog before wider rollout.
