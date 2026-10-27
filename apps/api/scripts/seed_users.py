"""Seed application users.

Usage (from apps/api):
    uv run python scripts/seed_users.py <email> <name> <password> <roles-csv> [language]

Example:
    uv run python scripts/seed_users.py dispatcher@example.local "Karolina" \\
        secret123 dispatcher en

Existing users (by email) are updated: name, roles and language only.
"""

import asyncio
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models import LANGUAGES, ROLES, User
from app.security import hash_password


async def seed(email: str, name: str, password: str, roles: list[str], language: str) -> None:
    invalid = [r for r in roles if r not in ROLES]
    if invalid:
        raise SystemExit(f"Unknown roles {invalid}; allowed: {ROLES}")
    if language not in LANGUAGES:
        raise SystemExit(f"Language must be one of {LANGUAGES}")
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                email=email.lower(),
                name=name,
                password_hash=hash_password(password),
                roles=roles,
                language=language,
            )
            session.add(user)
            print(f"created user {email} roles={roles} lang={language}")
        else:
            user.name = name
            user.roles = roles
            user.language = language
            print(f"updated user {email} roles={roles} lang={language} (password unchanged)")
        await session.commit()


def main() -> None:
    if len(sys.argv) not in (5, 6):
        raise SystemExit(__doc__)
    email, name, password, roles_csv = sys.argv[1:5]
    language = sys.argv[5] if len(sys.argv) == 6 else "en"
    roles = [r.strip() for r in roles_csv.split(",") if r.strip()]
    asyncio.run(seed(email, name, password, roles, language))


if __name__ == "__main__":
    main()
