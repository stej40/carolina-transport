# Tasks: MVP1 auth & users

Bootstrap and M1 of the original plan, already implemented and verified.

## M0 - Monorepo scaffold (DONE, recorded here as bootstrap)
- [x] pnpm workspace + uv backend, Vite apps, infra compose (postgres:18, garage), Makefile targets dev/test/lint/typecheck
- [x] `/api/v1/health` endpoint with smoke test (`apps/api/scripts/smoke_s3.py` verifies Garage presigned S3)

## M1 - Auth & users (DONE)
- [x] JWT access/refresh token flow with rotation
- [x] RBAC roles dispatcher/driver enforced on all endpoints
- [x] argon2 password hashing, user seed script
- [x] User profile with language preference (cs/en/de, validated) + authenticated profile endpoint incl. PATCH of preference
- [x] Auth tests covering happy paths and rejections
- [x] Expand roles to driver/dispatcher/company-admin/system-admin (models, seed, RBAC deps) + admin user-management endpoints (create/deactivate)
