# Proposal: API environment profiles (.env.local / .env.prod)

## Why

The API today loads a single hard-coded `.env` file (`apps/api/app/config.py`),
so local runs and production must share one file shape and developers rely on
in-code defaults (including the dev-only `SECRET_KEY`). Jiří needs an explicit,
git-ignored `.env.local` for local development with `DEBUG=true`, and a
separate `.env.prod` for production with debug disabled, selected by a single
`APP_ENV` switch.

## What Changes

- Settings loading becomes profile-driven: `APP_ENV` (`local` | `prod`,
  default `local`) selects `apps/api/.env.<profile>` as the dotenv file; real
  environment variables keep priority over file values (pydantic-settings
  default), so `infra/docker-compose.yml` inline env vars keep working.
- New `apps/api/.env.local.example` template (debug enabled) committed to git;
  the generic `.env.example` is removed - the per-profile example files replace
  it. Actual
  `.env.local` / `.env.prod` are created by developers/operators on their
  machines and never committed (already covered by `.gitignore` rules
  `.env.*` already ignored, negations added for the two example files).
- Production safety guard: when `APP_ENV=prod`, startup fails fast if the
  selected env file is missing or if `SECRET_KEY` still equals the shipped
  dev placeholder. `DEBUG` must be `false` in prod (docs/OpenAPI endpoints
  stay disabled, as today via `settings.debug` in `app/main.py`).
- `make api-dev` documents/sets `APP_ENV=local`; README gets a short
  env-profiles section.
- Local docker run: the dev compose `api` service bind-mounts
  `apps/api/.env.local` read-only into the container and keeps inline env
  only for container-network endpoints (DB, S3), so the mounted file drives
  everything else (added during Jiří's review).

Out of scope: dispatcher-web / driver-pwa env handling (they read no env vars
today), secret managers, CI changes, the production compose stack and Caddy
(which belong to in-flight `mvp1-deploy-pilot` - this change only makes the
API's config contract ready for it; the dev `api` service mount is local-only).

## Capabilities

### New Capabilities

- `runtime-configuration`: how the API resolves its settings - env profile
  selection by `APP_ENV`, file-vs-environment precedence, debug flag behavior,
  and production fail-fast validation.

### Modified Capabilities

(none - no archived spec changes requirement-level behavior; `portal-settings`
is a domain feature, not runtime config)

## Impact

- `apps/api/app/config.py` (dynamic `env_file`, validation), `app/main.py`
  unchanged in behavior.
- `apps/api/.env.example` deleted; new `.env.local.example`, `.env.prod.example`.
- `infra/docker-compose.yml` dev `api` service (env slimming + bind mount),
  `make infra-full` / `infra-down` targets.
- `Makefile`, `README.md`; tests under `apps/api/tests/` for profile
  selection and prod guard.
- Interacts with `mvp1-deploy-pilot`: its prod compose can later supply
  `.env.prod` on the VPS; no file conflict (it owns `infra/`, this owns the
  API settings contract).
