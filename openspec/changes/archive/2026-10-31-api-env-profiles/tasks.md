# Tasks

## 1. Profile resolution in settings

- [x] 1.1 Add `_resolve_env_profile()` helper in `apps/api/app/config.py` reading `APP_ENV` (default `local`), mapping to `.env.local` / `.env.prod`, raising on unknown values, and wire it into `Settings.model_config` `env_file`; verify with unit tests covering default, both profiles, and rejection of `APP_ENV=staging`.
- [x] 1.2 Add prod safety `model_validator` (env file present, `SECRET_KEY` not placeholder and length >= 32, `DEBUG` not true); verify with tests using `_env_file=`/`cache_clear()` per design decision 5.
- [x] 1.3 Confirm process-env-over-dotenv precedence holds by adding a test asserting `monkeypatch.setenv("DATABASE_URL", ...)` wins over a dotenv value; run `make api-test`.

## 2. Templates and repo hygiene

- [x] 2.1 Create `apps/api/.env.local.example` (`DEBUG=true`, local infra values) and `apps/api/.env.prod.example` (`DEBUG=false`, placeholder secrets); remove the generic `.env.example`; verify both examples parse as key lists matching `Settings` fields.
- [x] 2.2 Replace `!.env.example` with `!.env.local.example` / `!.env.prod.example` negations in `.gitignore` and verify with `git check-ignore -v` that examples are tracked while `.env.local`/`.env.prod` stay ignored.

## 3. Developer workflow docs & make

- [x] 3.1 Set `APP_ENV=local` explicitly in the `api-dev` Makefile target and verify `make api-dev` boots against defaults when no `.env.local` exists.
- [x] 3.2 Add a README "Environment profiles" section (`.env` -> `.env.local` migration note, prod VPS placement of `.env.prod` + `APP_ENV=prod` pointer for deploy-pilot); verify the documented copy+run steps work from a fresh clone.

## 4. Integration check

- [x] 4.1 End-to-end: `cp .env.local.example .env.local`, `make infra && make api-dev`, confirm `/api/docs` served (debug on); boot with `APP_ENV=prod` and no `.env.prod` and confirm the expected startup failure names the missing file; run `make lint && make typecheck && make api-test`.

## 5. Local docker env file (added in review)

- [x] 5.1 Slim the compose `api` service inline `environment:` to `DATABASE_URL` + `S3_ENDPOINT`, bind-mount `../apps/api/.env.local:/app/.env.local:ro`, document the `cp` precondition in README; verify with `docker compose -f infra/docker-compose.yml --profile full up -d api` that health returns 200 and `/api/docs` returns 200 (DEBUG from file) while the app connects to `postgres`/`garage`.
- [x] 5.2 Add `make infra-full` (compose up with `--profile full`) and make `infra-down` pass `--profile full` so the api container is stopped too; update Makefile help + README useful-commands; verify with a full `make infra-down && make infra-full` cycle ending in api `Up` and health 200.
