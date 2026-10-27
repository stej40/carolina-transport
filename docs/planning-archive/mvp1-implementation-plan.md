# MVP1 Implementation Plan – System KAROLINA

> Navazuje na [high-level-context.md](./high-level-context.md) a [plan-system-karolina.md](./plan-system-karolina.md).
> Tento dokument pokrývá **MVP1** – dispečerský web portál + mobilní PWA pro řidiče, sběr a kontrolu dokumentů, stavy přepravy.
> Integrace POHODA / banka / OCR / AI asistent jsou záměrně **mimo MVP1**, ale systém se navrhuje tak, aby je později šlo přidat bez refactoringu.

---

## 1. Locked decisions

| Area | Decision |
|---|---|
| Database | PostgreSQL 18 (Docker image `postgres:18-alpine`) |
| Backend | Python 3.13.7 (pyenv/uv pinned), FastAPI, SQLAlchemy 2.x (async) + asyncpg, Alembic, Pydantic v2 |
| File storage | **Garage 2.4** (S3 API, single container), presigned uploads – driver photos go directly to Garage, not through the API |
| Dispatcher frontend | React + TypeScript + Vite, TanStack Query + Router, Tailwind + shadcn/ui |
| Driver frontend | Offline-first PWA (own Vite app, `vite-plugin-pwa`, Dexie.js/IndexedDB, outbox sync) |
| API versioning | `/api/v1` from day one; OpenAPI spec is the contract for future native iOS/Android apps |
| Auth | Own JWT module: access + refresh tokens, RBAC roles (`dispatcher`, `driver`), argon2 password hashing |
| Monorepo | pnpm workspaces + uv: `apps/api`, `apps/dispatcher-web`, `apps/driver-pwa`, `packages/shared`, `infra/` |
| Deployment | Self-hosted VPS, Docker Compose + Caddy (TLS), backups (pg_dump + Garage S3 mirror to second bucket) |

> **Proč ne MinIO:** MinIO community edition byl 25. 4. 2026 archivován – keine Docker image, keine binárky, distribuce pouze ze zdroje (komerční nástupce = AIStor). Garage je aktivně maintained, MIT, single-binary, plně S3 kompatibilní (presigned URLs ověřeny testem `apps/api/scripts/smoke_s3.py`).
| Schema design | **Deliberately deferred** – produced as the signed-off deliverable of M2 (discovery), not pre-designed |

---

## 2. Data-model constraints to honor (input for M2, not the schema itself)

When the schema is designed in M2, it must satisfy these constraints. They are the cheap-now / expensive-later decisions:

1. **Billing-ready order data** – orders will later need quantity, unit, unit price, currency, VAT, billing text for the POHODA faktura export (MVP2). Don't model orders as pure logistics records.
2. **Variable symbol (VS)** – the invoicing concept must carry a VS generated/owned by our system so bank payments can be paired by VS + amount (MVP4). VS strategy gets confirmed with real POHODA practice during discovery.
3. **UUID primary keys, client-generatable** – required for offline document creation in the driver PWA and later for native apps.
4. **Idempotency keys on all write endpoints** – offline outbox replays writes; duplicates must be safe.
5. **Money as NUMERIC** (not float), rounding policy agreed once, up front.
6. **Immutable event log** for transport state transitions – audit today; enables webhooks / MCP / AI assistant later.
7. **External-ID mapping** per entity (system, external_id) – for idempotent two-way sync with POHODA without polluting core tables.
8. **Document taxonomy as data** – document types (vážní lístek nakládka/výkladka, čištění korby, objednávka…) with required attributes per type, defined from real paperwork samples in M2.

---

## 3. Discovery working model (M2)

Owner of raw material: **Jiří**. Analyst: **AI agent**. No real paperwork access yet, so the process is:

### Checklist – materials for Jiří to gather (anonymized!)
- [ ] Photos/scans of each document type: objednávka o přepravě, vážní lístek (nakládka), vážní lístek (výkladka), doklad o vyčištění korby, „a další dokumenty…"
      → **black out IČO, SPZ, names** before sharing.
- [ ] ~1h recorded walkthrough / structured Q&A with Karolina (or process-knowledge holder):
      what she checks per document, what is usually missing/wrong, how she decides a přeprava is complete, what blocks fakturaci.
- [ ] Current POHODA edition + how faktury and VS are created today (relevant for MVP2/MVP4, cheap to ask now).
- [ ] Volumes: přepravy/month, documents per přeprava, number of drivers, dispatcher count.
- [ ] Bank: account statement format today (CSV/PDF), current VS/SS pairing conventions.

### Deliverables of M2 (after materials arrive)
1. Document taxonomy + required attributes per document type.
2. Transport state machine (validated against Karolina's real workflow).
3. **Schema proposal document → signed off by Jiří** before any migration is written.
4. Refined MVP2–M4 estimates + updated risk list (POHODA mServer edition check is a hard gate).

---

## 4. Milestones

| # | Deliverable | Exit criteria | Est. (AI-assisted days) |
|---|---|---|---|
| **M0** | Monorepo scaffold: pnpm workspace, uv backend, Vite apps, docker-compose (pg18, garage, api), Makefile, CI (lint, typecheck, tests) | `make dev` boots stack, `/api/v1/health` OK, CI green | 2–3 |
| **M1** | Auth & users: JWT access/refresh, RBAC, user seed script | auth flow covered by tests | 3 |
| **M2** | **Domain discovery → approved datový model + state machine** (planning only, no code) | Jiří signs off schema doc | 1–2 + waiting on materials |
| **M3** | Core CRUD + transport state machine + immutable event log, built on approved schema (UUID PKs, idempotency) | API tests per state transition | 5–7 |
| **M4** | Dispatcher portal: dashboard per stav, create objednávka, assign driver, transport detail view | end-to-end test, clickable | 6–8 |
| **M5** | Documents: presigned upload to Garage (S3), manual data entry (no OCR), approve/reject loop, completeness check | e2e test incl. missing-doc flow | 5–6 |
| **M6** | Driver PWA (online): login, current přeprava, status actions, camera capture → upload | tested on a real phone | 4–6 |
| **M7** | Offline-first: IndexedDB cache, outbox queue, sync manager, conflict guards | airplane-mode Playwright test | 7–10 |
| **M8** | VPS deploy: Caddy/TLS, backups (pg_dump cron + Garage s3 mirror), healthcheck monitoring, pilot with 2–3 drivers | pilot running | 3–5 |

**Total: ≈ 36–47 focused days** (excl. discovery waiting time).

---

## 5. Explicitly deferred (and where they plug in)

| Feature | MVP | Plug-in point |
|---|---|---|
| POHODA integration (faktura write + e-mail) | MVP2 | `APPROVED` transition emits event → outbox job → POHODA adapter (`integrations/pohoda/`) |
| Bank payment pairing | MVP4 | daily statement import job → match on VS + amount → mark invoice paid |
| OCR/AI extraction of vážní lístky | MVP3 | document `data` JSONB already exists; OCR fills it, human confirms |
| AI assistant (LangChain/MCP) | MVP5 | MCP server exposes `/api/v1` read tools + event log |
| Native iOS/Android app | later | reuses `/api/v1` OpenAPI spec; PWA UX learnings transfer |
| Push notifications | later | replace PWA polling of dispatcher messages |

---

## 6. Risks (MVP1-relevant)

| Risk | Mitigation |
|---|---|
| Offline sync complexity underestimated | It's M7, after everything else works online; outbox+idempotency design forced from M3, not bolted on |
| Driver adoption (IT gramotnost) | M8 pilot with 2–3 drivers; giant-button UX; PWA installable, no app store |
| Paperwork reality differs from assumption | M2 discovery gate before any domain code is written |
| Legal status of photographed doklady (metrická exigeance u vážních lístků, daňová způsobilost) | Flag to Jiří in M2; may require keeping paper originals in MVP1 — design doesn't block either outcome |
| VPS ops (backups, TLS, updates) | M8 runbook; start with managed Postgres later if ops load grows |

---

## 7. Repository layout (M0)

```
agro-karolina/
├── apps/
│   ├── api/               # FastAPI (uv, .python-version = 3.13.7)
│   ├── dispatcher-web/    # React + TS + Vite (desktop portal)
│   └── driver-pwa/        # React + TS + Vite + vite-plugin-pwa (offline-first)
├── packages/
│   └── shared/            # generated API types (openapi-typescript), shared UI/utils
├── infra/
│   ├── docker-compose.yml # postgres:18, garage (s3), api
│   ├── garage.toml        # single-node dev config
│   └── Caddyfile          # prod TLS (M8)
├── .github/workflows/ci.yml
├── Makefile               # dev, test, lint, typecheck, build
└── mvp1-implementation-plan.md
```

---

## 8. Definition of Done for MVP1

A dispečer can create an objednávka, assign a přepravu; a řidič (even with no signal during loading) records statuses and documents; documents flow through review (approve / request-correction); přeprava closes with a complete, auditable file. Paper is out of the loop for at least the pilot drivers. No faktura is produced by the system yet — that is MVP2, and MVP1's data is ready for it.
