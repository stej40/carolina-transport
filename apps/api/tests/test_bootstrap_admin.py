"""API tests for the bootstrap-system-admin change (startup admin guarantee)."""

import logging
from collections.abc import Awaitable, Callable

import pytest
from conftest import bearer, login
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import bootstrap
from app.bootstrap import RESULT_CREATED, RESULT_NOT_NEEDED, RESULT_REVIVED, ensure_system_admin
from app.config import DEV_BOOTSTRAP_PASSWORD, Settings
from app.models import User
from app.security import verify_password

Pw = "secret123"
BOOT_EMAIL = "sysadmin@bootstrap.test"
BOOT_PASSWORD = "bootstrap-password-123"


@pytest.fixture
def bootstrap_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setattr(bootstrap.settings, "bootstrap_admin_email", BOOT_EMAIL)
    monkeypatch.setattr(bootstrap.settings, "bootstrap_admin_password", BOOT_PASSWORD)
    return bootstrap.settings


async def _rows(maker: async_sessionmaker[AsyncSession]) -> list[User]:
    async with maker() as session:
        return list((await session.execute(select(User))).scalars().all())


async def test_fresh_database_gets_a_usable_system_admin(
    session_maker: async_sessionmaker[AsyncSession],
    client: AsyncClient,
    bootstrap_settings: Settings,
) -> None:
    result = await ensure_system_admin(session_maker)
    assert result == RESULT_CREATED

    rows = await _rows(session_maker)
    assert len(rows) == 1
    user = rows[0]
    assert user.email == BOOT_EMAIL.lower()
    assert user.is_active and user.roles == ["system-admin"]

    tokens = await login(client, BOOT_EMAIL, BOOT_PASSWORD)
    me = await client.get("/api/v1/auth/me", headers=bearer(tokens["access_token"]))
    assert me.json()["id"] == str(user.id)

    # the configured password is used; the dev placeholder is not
    assert verify_password(BOOT_PASSWORD, user.password_hash)
    assert not verify_password(DEV_BOOTSTRAP_PASSWORD, user.password_hash)


async def test_second_run_is_a_no_op(
    session_maker: async_sessionmaker[AsyncSession], bootstrap_settings: Settings
) -> None:
    assert await ensure_system_admin(session_maker) == RESULT_CREATED
    before = await _rows(session_maker)
    assert await ensure_system_admin(session_maker) == RESULT_NOT_NEEDED
    after = await _rows(session_maker)
    assert [u.id for u in after] == [u.id for u in before]
    assert after[0].password_hash == before[0].password_hash


async def test_existing_active_admin_leaves_everything_untouched(
    session_maker: async_sessionmaker[AsyncSession],
    add_user: Callable[..., Awaitable[User]],
    bootstrap_settings: Settings,
) -> None:
    await add_user("boss@example.test", password=Pw, roles=["system-admin"])
    stale = await add_user(BOOT_EMAIL, password="old-password", roles=["driver"])
    async with session_maker() as session:
        row = await session.get(User, stale.id)
        assert row is not None
        row.is_active = False  # disabled and demoted bootstrap account
        session.add(row)
        await session.commit()

    assert await ensure_system_admin(session_maker) == RESULT_NOT_NEEDED

    by_email = {u.email: u for u in await _rows(session_maker)}
    untouched = by_email[BOOT_EMAIL]
    assert untouched.is_active is False
    assert untouched.roles == ["driver"]
    assert verify_password("old-password", untouched.password_hash)
    assert by_email["boss@example.test"].roles == ["system-admin"]


async def test_lockout_revives_account_and_resets_password(
    session_maker: async_sessionmaker[AsyncSession],
    client: AsyncClient,
    add_user: Callable[..., Awaitable[User]],
    bootstrap_settings: Settings,
) -> None:
    stale = await add_user(
        BOOT_EMAIL, password="old-password", roles=["system-admin", "dispatcher"]
    )
    async with session_maker() as session:
        row = await session.get(User, stale.id)
        assert row is not None
        row.is_active = False  # lock-out: last system-admin disabled
        session.add(row)
        await session.commit()

    assert await ensure_system_admin(session_maker) == RESULT_REVIVED

    user = (await _rows(session_maker))[0]
    assert user.is_active
    assert "system-admin" in user.roles and "dispatcher" in user.roles
    assert not verify_password("old-password", user.password_hash)
    assert verify_password(BOOT_PASSWORD, user.password_hash)
    await login(client, BOOT_EMAIL, BOOT_PASSWORD)
    bad = await client.post(
        "/api/v1/auth/login", json={"email": BOOT_EMAIL, "password": "old-password"}
    )
    assert bad.status_code == 401


async def test_password_never_appears_in_logs(
    session_maker: async_sessionmaker[AsyncSession],
    bootstrap_settings: Settings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="app.bootstrap"):
        await ensure_system_admin(session_maker)
        await ensure_system_admin(session_maker)
    assert BOOT_PASSWORD not in caplog.text
    assert BOOT_EMAIL not in caplog.text
    assert RESULT_CREATED in caplog.text and RESULT_NOT_NEEDED in caplog.text
