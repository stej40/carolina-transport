import uuid
from collections.abc import Awaitable, Callable

from conftest import bearer, idem, login
from httpx import AsyncClient

from app.models import User


async def admin_headers(
    client: AsyncClient,
    add_user: Callable[..., Awaitable[User]],
    role: str = "company-admin",
) -> dict[str, str]:
    email = f"{role}@example.com"
    await add_user(email, password="secret123", roles=[role], name="Admin")
    tokens = await login(client, email, "secret123")
    return bearer(tokens["access_token"])


async def test_company_admin_creates_dispatcher_who_can_sign_in(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    headers = await admin_headers(client, add_user)
    created = await client.post(
        "/api/v1/users",
        json={
            "email": "New.Dispatcher@Example.com",
            "name": "Nina",
            "password": "newpassword1",
            "roles": ["dispatcher"],
        },
        headers={**headers, **idem()},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["email"] == "new.dispatcher@example.com"
    assert body["roles"] == ["dispatcher"]
    assert body["is_active"] is True

    tokens = await login(client, "new.dispatcher@example.com", "newpassword1")
    assert tokens["access_token"]


async def test_dispatcher_and_driver_cannot_create_users(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    await add_user("disp@example.com", roles=["dispatcher"])
    await add_user("drv@example.com", roles=["driver"])
    for email in ("disp@example.com", "drv@example.com"):
        tokens = await login(client, email)
        denied = await client.post(
            "/api/v1/users",
            json={
                "email": "x@example.com",
                "name": "X",
                "password": "whatever12",
                "roles": ["driver"],
            },
            headers={**bearer(tokens["access_token"]), **idem()},
        )
        assert denied.status_code == 403


async def test_only_system_admin_may_create_admin_accounts(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    company = await admin_headers(client, add_user, "company-admin")
    blocked = await client.post(
        "/api/v1/users",
        json={
            "email": "boss@example.com",
            "name": "Boss",
            "password": "password123",
            "roles": ["system-admin"],
        },
        headers={**company, **idem()},
    )
    assert blocked.status_code == 403

    await add_user("root@example.com", roles=["system-admin"], name="Root")
    root = bearer((await login(client, "root@example.com"))["access_token"])
    allowed = await client.post(
        "/api/v1/users",
        json={
            "email": "admin2@example.com",
            "name": "Ada",
            "password": "password123",
            "roles": ["company-admin"],
        },
        headers={**root, **idem()},
    )
    assert allowed.status_code == 201


async def test_duplicate_email_conflict_and_invalid_role(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    await add_user("dup@example.com", roles=["driver"])
    headers = await admin_headers(client, add_user)
    conflict = await client.post(
        "/api/v1/users",
        json={
            "email": "dup@example.com",
            "name": "D",
            "password": "password123",
            "roles": ["driver"],
        },
        headers={**headers, **idem()},
    )
    assert conflict.status_code == 409

    bad_role = await client.post(
        "/api/v1/users",
        json={"email": "w@x.cz", "name": "W", "password": "password123", "roles": ["root"]},
        headers={**headers, **idem()},
    )
    assert bad_role.status_code == 422


async def test_deactivation_blocks_signin_and_live_session(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    victim = await add_user("gone@example.com", roles=["dispatcher"])
    tokens = await login(client, "gone@example.com")
    headers = await admin_headers(client, add_user)

    off = await client.post(f"/api/v1/users/{victim.id}/deactivate", headers={**headers, **idem()})
    assert off.status_code == 200
    assert off.json()["is_active"] is False

    failed = await client.post(
        "/api/v1/auth/login", json={"email": "gone@example.com", "password": "secret123"}
    )
    assert failed.status_code == 401
    assert failed.json()["detail"] == "Invalid credentials"

    live = await client.get("/api/v1/auth/me", headers=bearer(tokens["access_token"]))
    assert live.status_code == 401

    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 401


async def test_company_admin_cannot_deactivate_admin(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    admin2 = await add_user("admin2@example.com", roles=["company-admin"], name="Two")
    headers = await admin_headers(client, add_user, "company-admin")
    denied = await client.post(
        f"/api/v1/users/{admin2.id}/deactivate", headers={**headers, **idem()}
    )
    assert denied.status_code == 403

    await add_user("root@example.com", roles=["system-admin"], name="Root")
    root = bearer((await login(client, "root@example.com"))["access_token"])
    allowed = await client.post(f"/api/v1/users/{admin2.id}/deactivate", headers={**root, **idem()})
    assert allowed.status_code == 200


async def test_deactivate_unknown_user_404(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    headers = await admin_headers(client, add_user)
    missing = await client.post(
        f"/api/v1/users/{uuid.uuid4()}/deactivate", headers={**headers, **idem()}
    )
    assert missing.status_code == 404
