"""Startup guarantee: the API always has at least one active system-admin.

Called from the lifespan hook (see main.py). Idempotent across restarts and
replicas; the invariant is "an active user holding the system-admin role".
Design: openspec/changes/bootstrap-system-admin (decisions 2, 3, 5).
"""

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.models import User
from app.security import hash_password

RESULT_CREATED = "created"
RESULT_REVIVED = "revived"
RESULT_NOT_NEEDED = "not-needed"
RESULT_CREATED_CONCURRENTLY = "created-concurrently"

logger = logging.getLogger("app.bootstrap")
if not logger.handlers:
    # No root handler under uvicorn - attach one so the INFO line is visible.
    # The password is never part of any log record.
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s: %(name)s: %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


async def _has_active_system_admin(session: AsyncSession) -> bool:
    """Roles are a JSON list, so membership is filtered in Python - identical
    behaviour on PostgreSQL and the SQLite test database."""
    rows = await session.execute(select(User.roles).where(User.is_active.is_(True)))
    return any("system-admin" in roles for roles in rows.scalars())


async def ensure_system_admin(maker: async_sessionmaker[AsyncSession]) -> str:
    email = settings.bootstrap_admin_email.lower()
    async with maker() as session:
        if await _has_active_system_admin(session):
            result = RESULT_NOT_NEEDED
        else:
            existing = await session.scalar(select(User).where(User.email == email))
            if existing is not None:
                existing.is_active = True
                if "system-admin" not in existing.roles:
                    existing.roles = [*existing.roles, "system-admin"]
                existing.password_hash = hash_password(settings.bootstrap_admin_password)
                session.add(existing)
                result = RESULT_REVIVED
            else:
                session.add(
                    User(
                        email=email,
                        name="System Administrator",
                        password_hash=hash_password(settings.bootstrap_admin_password),
                        roles=["system-admin"],
                        is_active=True,
                    )
                )
                result = RESULT_CREATED
        try:
            await session.commit()
        except IntegrityError:
            # Another replica won the race on the unique e-mail index.
            await session.rollback()
            if result == RESULT_CREATED:
                result = RESULT_CREATED_CONCURRENTLY
    logger.info("system-admin bootstrap: %s", result)
    return result
