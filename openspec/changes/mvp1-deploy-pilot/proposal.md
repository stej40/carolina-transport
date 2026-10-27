# Proposal: MVP1 deployment & pilot

## Why
The system replaces an office job only once it runs reliably outside dev
machines: self-hosted VPS with TLS, real backups an operator can restore,
monitoring, and a small driver pilot proving adoption before rollout.

## What Changes
- New capability `platform-deployment`: deployable Compose stack behind Caddy
  (TLS), automated pg_dump + Garage mirror backups with documented restore,
  health endpoint + operator alerting.
- Pilot with 2-3 drivers; MVP1 Definition of Done evaluated there.

## Out of scope
Managed cloud services, CI/CD beyond the existing pipeline, MVP2 integrations.

## Capabilities
### New Capabilities
- `platform-deployment`

### Modified Capabilities
(none)

## Impact
- `infra/` prod compose + Caddyfile, runbook in `docs/runbook/`, backup cron,
  monitoring hook.

**Depends on:** all functional MVP1 changes (ships last).

## MVP1 Definition of Done (final acceptance lives here)
A dispatcher creates an order and assigns a transport; a driver (even with no
signal at loading) records statuses and documents; documents flow through
review; the transport closes with a complete, auditable file. Paper is out of
the loop for pilot drivers. No invoice produced yet - data is MVP2-ready.
