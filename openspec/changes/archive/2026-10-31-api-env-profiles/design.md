# Design

## Context

`apps/api/app/config.py` defines a pydantic `Settings` with a hard-coded
`env_file=".env"` and dev defaults (including a placeholder `SECRET_KEY`);
`settings = get_settings()` is imported eagerly by `main.py`, `db.py`,
`security.py`, routers and Alembic's `migrations/env.py`. `DEBUG` currently
only toggles `/api/docs` + `/api/openapi.json` (`main.py:37-38`). Dev runs
from `apps/api/` via `make api-dev`; the compose `api` service injects real
env vars inline. See proposal.md - Why for motivation.

## Goals / Non-Goals

**Goals:**
- One switch (`APP_ENV`) selects the dotenv file; defaults keep `make api-dev`
  and the test suite working with zero setup.
- Prod profile refuses to boot in an unsafe state instead of silently using
  dev values.
- Existing precedence (process env > dotenv) preserved so today's compose
  inline vars keep winning.

**Non-Goals:**
- Frontend (Vite) env handling; secret managers; changing what `DEBUG` gates
  beyond current docs/OpenAPI endpoints.

## Decisions

1. **`APP_ENV` read via `os.environ` at settings build time**, validated
   against `{"local", "prod"}` (default `local`); the env file becomes
   `.env.local` / `.env.prod` relative to the API working directory
   (`apps/api/`). Alternative: an `ENV_FILE` path variable - rejected because
   the user chose a named-profile switch and unknown paths invite typos; the
   profile check turns a typo into a loud error.
2. **Validation in a `model_validator(mode="after")` on `Settings`**, keyed on
   the resolved profile stored as a private attr: for `prod`, fail if the env
   file is absent, if `secret_key` equals the shipped placeholder, or if
   `debug` is true. Alternative: silently coerce `debug=False` in prod -
   rejected: a mis-shipped `.env.prod` should be a deploy error, not a
   surprise. For `local`, missing file → defaults, as pydantic-settings
   already ignores absent dotenv files (no code needed).
3. **Compose `api` service stays on the default profile but mounts the local
   env file.** `infra/docker-compose.yml` does not set `APP_ENV`; it
   bind-mounts `apps/api/.env.local` to `/app/.env.local` (read-only) so a
   local `--profile full` run uses the same dotenv path production will use,
   and keeps inline `environment:` only for the two values that must differ
   inside the container network (`DATABASE_URL` -> `postgres:5432`,
   `S3_ENDPOINT` -> `garage:3900`) - process-env-over-dotenv precedence makes
   them win over the file. All other inline vars are dropped so `.env.local`
   drives `DEBUG`, `SECRET_KEY`, TTLs, S3 credentials, CORS. Precondition for
   developers: `cp apps/api/.env.local.example apps/api/.env.local` first
   (bind-mounting a missing file makes Docker create an empty directory).
   Recreating with `--force-recreate` is needed after the network is rebuilt
   (e.g. `make infra` after a Docker restart leaves the old stopped api
   pointing at a stale network id - covered by `make infra-full`).
   Production on the VPS (owned by
   `mvp1-deploy-pilot`) sets `APP_ENV=prod` and bind-mounts or copies
   `/etc/karolina/.env.prod` to `apps/api/.env.prod` in the image's working
   dir - documented in README, implemented there, not here.
4. **Two committed templates**: `.env.local.example` (documents `APP_ENV` +
   all keys, local-flavoured) and `.env.prod.example` (same keys,
   `DEBUG=false`, placeholder secrets); the generic `.env.example` is deleted
   as it duplicated the local template. Plain `.env` is retired; README tells
   owners to move any existing `.env` to `.env.local`. `.gitignore` drops
   `!.env.example` and adds `!` negations for the two example files (`.env.*`
   keeps ignoring the real `.env.local` / `.env.prod`).
5. **Testability**: profile resolution lives in a small pure helper
   `_resolve_env_profile() -> tuple[str, Path]`; tests build settings with
   pydantic-settings' `_env_file=` runtime kwarg and `get_settings.cache_clear()`
   rather than touching real files or process env globally.
6. **Makefile**: `api-dev` runs with `APP_ENV=local` explicitly set (self-
   documenting even though it is the default). `make infra-full` starts the
   whole dev stack incl. the api container (profile `full`); `infra-down`
   passes `--profile full` so it also stops api (found in review: profiled
   services are outside a plain `down`).

## Risks / Trade-offs

- [Existing developer `.env` files stop being read] → README migration note +
  line in `api-dev` help; one-time copy is trivial.
- [Eager module-level `settings` import means validation errors surface at
  import time, before uvicorn logs] → acceptable (fail-fast), error message
  names the offending key.
- [Prod file path depends on container WORKDIR `/app`] → pinned in README
  runbook line and covered by deploy-pilot; smoke test `APP_ENV=prod` boot in
  CI-less manual checklist.
- [`SECRET_KEY` placeholder comparison is string-equality] → also require
  length ≥ 32 in prod validator so renamed-but-weak secrets still fail.

## Migration Plan

Deploy: create `.env.local` from template locally; on the VPS (during
deploy-pilot) create `/app/.env.prod` from `.env.prod.example`, set
`APP_ENV=prod` in the prod compose. Rollback: revert `config.py`; the old
`.env` mechanism is a strict subset (defaults unchanged).
