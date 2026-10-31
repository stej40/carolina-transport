# runtime-configuration Specification

## Purpose

Defines how the API resolves its runtime configuration: selecting an
environment profile (local vs production) via `APP_ENV`, precedence between
dotenv files and real environment variables, and debug-related behavior of
the served application.

## Requirements

### Requirement: Environment profile selection
The API SHALL resolve its configuration from an environment profile named by
`APP_ENV` with allowed values `local` and `prod`, defaulting to `local` when
unset. Profile `local` SHALL load settings from `apps/api/.env.local`, and
profile `prod` SHALL load settings from `apps/api/.env.prod`, if those files
exist. An unrecognized `APP_ENV` value SHALL cause startup to fail with an
error naming the invalid value.

#### Scenario: Default profile is local
- **WHEN** the API starts with `APP_ENV` unset and a `.env.local` file present
- **THEN** the values from `.env.local` are applied to settings

#### Scenario: Prod profile selects .env.prod
- **WHEN** the API starts with `APP_ENV=prod` and a `.env.prod` file present
- **THEN** the values from `.env.prod` are applied and `.env.local` is ignored

#### Scenario: Unknown profile rejected
- **WHEN** the API starts with `APP_ENV=staging`
- **THEN** startup fails with an error stating that `staging` is not a valid
  profile

### Requirement: Real environment variables take precedence
Values of actual process environment variables SHALL override the same keys
read from the profile dotenv file, so container-based deployments can inject
configuration without a file.

#### Scenario: Compose inline variable wins
- **WHEN** the API starts with `APP_ENV=prod`, `.env.prod` defining
  `DATABASE_URL=...file-value`, and process environment
  `DATABASE_URL=...process-value`
- **THEN** the effective `database_url` setting is `...process-value`

### Requirement: Debug flag controls development-only endpoints
When the effective `DEBUG` setting is true, the API SHALL serve the interactive
docs and the OpenAPI JSON endpoint; when false, both SHALL return 404 and no
other behavior SHALL depend on the flag being readable externally. The default
value of `DEBUG` SHALL be false.

#### Scenario: Debug enabled in local profile
- **WHEN** the API runs with profile `local` and `.env.local` containing
  `DEBUG=true`
- **THEN** `GET /api/docs` and `GET /api/openapi.json` are served

#### Scenario: Debug disabled in prod profile
- **WHEN** the API runs with profile `prod` and `.env.prod` containing
  `DEBUG=false`
- **THEN** `GET /api/docs` and `GET /api/openapi.json` respond 404

### Requirement: Production profile fails fast on unsafe configuration
When the effective profile is `prod`, the API SHALL refuse to start if
`SECRET_KEY` is missing or equal to the shipped development placeholder, or if
`DEBUG` resolves to true. When the effective profile is `local`, the API SHALL
start using built-in defaults even if `.env.local` is absent.

#### Scenario: Placeholder secret in prod
- **WHEN** the API starts with `APP_ENV=prod` and `SECRET_KEY` set to the
  development placeholder value
- **THEN** startup fails with an error identifying `SECRET_KEY` as the cause

#### Scenario: Debug forced off in prod
- **WHEN** the API starts with `APP_ENV=prod` and `DEBUG=true`
- **THEN** startup fails with an error stating debug must not be enabled in
  production

#### Scenario: Missing local file falls back to defaults
- **WHEN** a developer starts the API with `APP_ENV` unset and no `.env.local`
  file
- **THEN** the API starts with built-in development defaults

### Requirement: Profile files are never committed
`.env.local` and `.env.prod` SHALL remain outside version control, while a
committed example file for each documented profile SHALL exist showing every
supported key with non-secret placeholder values.

#### Scenario: Developer onboarding
- **WHEN** a new developer copies the local example file to `.env.local` and
  runs `make api-dev`
- **THEN** the API starts in debug mode against the local infra without
  consulting any undocumented variable

### Requirement: Local docker run uses the local profile file
The development compose stack SHALL make `apps/api/.env.local` available to
the API container in the same way production will use its profile file: the
file is mounted read-only into the container, and only container-network
values (database and object-storage endpoints) are supplied as process
environment variables so they take precedence over the file.

#### Scenario: Debug setting reaches the container
- **WHEN** `.env.local` contains `DEBUG=true` and the developer starts the
  compose `api` service with `--profile full`
- **THEN** the container serves `/api/docs` (debug on) while still connecting
  to the `postgres` and `garage` services rather than `localhost`
