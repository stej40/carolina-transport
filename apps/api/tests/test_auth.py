from collections.abc import Awaitable, Callable

from conftest import bearer, login
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import User


async def test_login_returns_tokens_and_me_works(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    await add_user("alice@example.com", roles=["dispatcher"])
    tokens = await login(client, "alice@example.com")
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]

    me = await client.get("/api/v1/auth/me", headers=bearer(tokens["access_token"]))
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "alice@example.com"
    assert body["roles"] == ["dispatcher"]
    assert body["language"] == "en"


async def test_login_unknown_email_and_wrong_password_are_generic_401(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    await add_user("bob@example.com", password="rightpass", roles=["driver"])

    unknown = await client.post(
        "/api/v1/auth/login", json={"email": "ghost@example.com", "password": "whatever"}
    )
    wrong = await client.post(
        "/api/v1/auth/login", json={"email": "bob@example.com", "password": "wrongpass"}
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


async def test_login_records_last_login(
    client: AsyncClient,
    add_user: Callable[..., Awaitable[User]],
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    user = await add_user("carl@example.com", roles=["driver"])
    assert user.last_login_at is None
    await login(client, "carl@example.com")
    async with session_maker() as session:
        fresh = await session.get(User, user.id)
        assert fresh is not None and fresh.last_login_at is not None


async def test_refresh_rotates_and_revokes_old(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    await add_user("dana@example.com", roles=["driver"])
    tokens = await login(client, "dana@example.com")

    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    replay = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert replay.status_code == 401

    ok = await client.get("/api/v1/auth/me", headers=bearer(new_tokens["access_token"]))
    assert ok.status_code == 200


async def test_logout_revokes_refresh(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    await add_user("emma@example.com", roles=["driver"])
    tokens = await login(client, "emma@example.com")

    out = await client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert out.status_code == 204

    after = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert after.status_code == 401


async def test_me_requires_valid_access_token(client: AsyncClient) -> None:
    missing = await client.get("/api/v1/auth/me")
    assert missing.status_code == 401
    garbage = await client.get("/api/v1/auth/me", headers=bearer("not-a-jwt"))
    assert garbage.status_code == 401


async def test_rbac_driver_cannot_list_users(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    await add_user("frank@example.com", roles=["driver"])
    await add_user("gina@example.com", roles=["dispatcher"])

    driver_tokens = await login(client, "frank@example.com")
    denied = await client.get("/api/v1/users", headers=bearer(driver_tokens["access_token"]))
    assert denied.status_code == 403

    disp_tokens = await login(client, "gina@example.com")
    allowed = await client.get("/api/v1/users", headers=bearer(disp_tokens["access_token"]))
    assert allowed.status_code == 200
    emails = {u["email"] for u in allowed.json()}
    assert {"frank@example.com", "gina@example.com"} <= emails


async def test_language_patch_validates(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    await add_user("hank@example.com", roles=["driver"])
    tokens = await login(client, "hank@example.com")
    headers = bearer(tokens["access_token"])

    bad = await client.patch("/api/v1/auth/me", json={"language": "sk"}, headers=headers)
    assert bad.status_code == 422

    ok = await client.patch("/api/v1/auth/me", json={"language": "cs"}, headers=headers)
    assert ok.status_code == 200
    assert ok.json()["language"] == "cs"

    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["language"] == "cs"
