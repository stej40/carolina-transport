# Design: MVP1 auth & users

Implemented design (recorded for archive):

- Own JWT module: HS256 access tokens (sub/roles/typ/exp/jti, 15 min default),
  opaque 48-byte refresh tokens stored SHA-256-hashed with rotation; reuse of a
  rotated token is rejected; deactivation blocks login, refresh and live
  access tokens (generic 401 at login, no account-existence leak).
- argon2id hashing (argon2-cffi, 64 MB / t=3 / p=2).
- `users` (UUID PK, email unique, roles JSON list, language cs/en/de,
  is_active, last_login_at) + `refresh_tokens` tables via Alembic 0001/0002.
- RBAC via `require_roles(...)` dependencies; `dispatcher_only`, `admin_only`,
  and `user_reader` (dispatcher or any admin) presets.
- Admin endpoints: `POST /api/v1/users`, `POST /api/v1/users/{id}/deactivate`;
  touching admin roles requires system-admin; duplicate email -> 409.
- Seeds: `scripts/seed_users.py`.
