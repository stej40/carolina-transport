"""Idempotency-Key middleware behaviour (constraint 4, offline replay)."""

from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from conftest import bearer, idem, login
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.idempotency import RETENTION_DAYS, purge_stale_idempotency_keys
from app.models import IdempotencyKey, User, utcnow

Pw = "secret123"


async def _dispatcher_headers(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> dict:
    await add_user("disp@example.com", password=Pw, roles=["dispatcher"], name="Disp")
    return bearer((await login(client, "disp@example.com", Pw))["access_token"])


def _order_payload(group_id: str, number: str) -> dict[str, Any]:
    return {
        "group_id": group_id,
        "number": number,
        "counterparty_name": "Agro Karolina a.s.",
        "cargo_text": "Umleti kuny",
        "quantity": "12.500",
        "unit": "t",
        "unit_price": "500.00",
        "vat_rate": "21.0",
        "loading_place": "Aretesy",
        "unloading_place": "Zastavka",
    }


async def test_replayed_request_returns_original_result_no_duplicate(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    disp = await _dispatcher_headers(client, add_user)
    await add_user("boss@example.com", password=Pw, roles=["company-admin"], name="Boss")
    admin = bearer((await login(client, "boss@example.com", Pw))["access_token"])
    group_id = (
        await client.post("/api/v1/groups", json={"name": "A"}, headers={**admin, **idem()})
    ).json()["id"]
    disp_id = (await client.get("/api/v1/auth/me", headers=disp)).json()["id"]
    assert (
        await client.put(
            f"/api/v1/groups/{group_id}/members/{disp_id}", headers={**admin, **idem()}
        )
    ).status_code == 204

    key = "5f0c0dec-0000-4000-8000-0123456789ab"
    body = _order_payload(group_id, "1")
    first = await client.post("/api/v1/orders", json=body, headers={**disp, "Idempotency-Key": key})
    assert first.status_code == 201, first.text
    replay = await client.post(
        "/api/v1/orders", json=body, headers={**disp, "Idempotency-Key": key}
    )
    assert replay.status_code == 201, replay.text
    assert replay.headers.get("idempotency-replayed") == "true"
    assert replay.json() == first.json()

    listed = (await client.get("/api/v1/orders", headers=disp)).json()
    assert len(listed) == 1

    # same key, different payload -> rejected, original untouched
    conflicting = await client.post(
        "/api/v1/orders",
        json=_order_payload(group_id, "2"),
        headers={**disp, "Idempotency-Key": key},
    )
    assert conflicting.status_code == 422
    assert len((await client.get("/api/v1/orders", headers=disp)).json()) == 1


async def test_failed_request_key_is_reusable(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    await add_user("boss@example.com", password=Pw, roles=["company-admin"], name="Boss")
    admin = bearer((await login(client, "boss@example.com", Pw))["access_token"])
    group_id = (
        await client.post("/api/v1/groups", json={"name": "A"}, headers={**admin, **idem()})
    ).json()["id"]
    disp = await _dispatcher_headers(client, add_user)
    disp_id = (await client.get("/api/v1/auth/me", headers=disp)).json()["id"]
    assert (
        await client.put(
            f"/api/v1/groups/{group_id}/members/{disp_id}", headers={**admin, **idem()}
        )
    ).status_code == 204

    bad = _order_payload(group_id, "1")
    del bad["cargo_text"]
    key = "11111111-2222-4333-8444-555555555555"
    failed = await client.post("/api/v1/orders", json=bad, headers={**disp, "Idempotency-Key": key})
    assert failed.status_code == 422
    retried = await client.post(
        "/api/v1/orders",
        json=_order_payload(group_id, "1"),
        headers={**disp, "Idempotency-Key": key},
    )
    assert retried.status_code == 201, retried.text


async def _admin_headers(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> dict[str, str]:
    await add_user("boss@example.com", password=Pw, roles=["company-admin"], name="Boss")
    return bearer((await login(client, "boss@example.com", Pw))["access_token"])


async def _row_count(session_maker: async_sessionmaker[AsyncSession]) -> int:
    async with session_maker() as session:
        result = await session.execute(select(func.count()).select_from(IdempotencyKey))
    return int(result.scalar_one())


async def test_write_without_key_rejected_400_then_succeeds_with_key(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    """Task 1.1: a covered write with no Idempotency-Key is a 400, no side effect."""
    admin = await _admin_headers(client, add_user)
    group_id = (
        await client.post("/api/v1/groups", json={"name": "A"}, headers={**admin, **idem()})
    ).json()["id"]
    body = {
        "email": "new@example.com",
        "name": "Nina",
        "password": "newpassword1",
        "roles": ["dispatcher"],
    }
    missing = await client.post("/api/v1/users", json=body, headers=admin)
    assert missing.status_code == 400
    assert "Idempotency-Key" in str(missing.json()["detail"])
    assert "new@example.com" not in {
        u["email"] for u in (await client.get("/api/v1/users", headers=admin)).json()
    }

    created = await client.post("/api/v1/users", json=body, headers={**admin, **idem()})
    assert created.status_code == 201, created.text

    victim = created.json()["id"]
    missing_del = await client.post(f"/api/v1/users/{victim}/deactivate", headers=admin)
    assert missing_del.status_code == 400
    deactivated = await client.post(
        f"/api/v1/users/{victim}/deactivate", headers={**admin, **idem()}
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["is_active"] is False

    missing_put = await client.delete(f"/api/v1/groups/{group_id}/members/{victim}", headers=admin)
    assert missing_put.status_code == 400


async def test_replay_on_non_domain_endpoint_returns_original_201(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    """Task 2.2: replay on POST /users (previously outside middleware scope)."""
    admin = await _admin_headers(client, add_user)
    body = {"email": "rep@example.com", "name": "Rep", "password": "passw0rd1", "roles": ["driver"]}
    key = "a1a2a3a4-0000-4000-8000-000000000001"
    first = await client.post("/api/v1/users", json=body, headers={**admin, "Idempotency-Key": key})
    assert first.status_code == 201, first.text
    replay = await client.post(
        "/api/v1/users", json=body, headers={**admin, "Idempotency-Key": key}
    )
    assert replay.status_code == 201
    assert replay.headers.get("idempotency-replayed") == "true"
    assert replay.json() == first.json()
    users = (await client.get("/api/v1/users", headers=admin)).json()
    assert [u for u in users if u["email"] == "rep@example.com"] == [first.json()]


async def test_replayed_empty_success_body(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    """Task 1.2: 204 stored as null body - replay answers 204, not 409 in flight."""
    admin = await _admin_headers(client, add_user)
    group_id = (
        await client.post("/api/v1/groups", json={"name": "A"}, headers={**admin, **idem()})
    ).json()["id"]
    disp = await _dispatcher_headers(client, add_user)
    disp_id = (await client.get("/api/v1/auth/me", headers=disp)).json()["id"]

    key = "b2b3b4b5-0000-4000-8000-000000000002"
    first = await client.put(
        f"/api/v1/groups/{group_id}/members/{disp_id}", headers={**admin, "Idempotency-Key": key}
    )
    assert first.status_code == 204, first.text
    replay = await client.put(
        f"/api/v1/groups/{group_id}/members/{disp_id}", headers={**admin, "Idempotency-Key": key}
    )
    assert replay.status_code == 204, replay.text
    assert replay.headers.get("idempotency-replayed") == "true"
    assert replay.content == b""
    detail = (await client.get(f"/api/v1/groups/{group_id}", headers=admin)).json()
    assert [m["id"] for m in detail["members"]] == [disp_id]


async def test_auth_endpoints_exempt_and_never_cached(
    client: AsyncClient,
    add_user: Callable[..., Awaitable[User]],
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Auth writes need no key and their credential responses stay out of the cache."""
    await add_user("twin@example.com", password=Pw, roles=["driver"])
    first = await login(client, "twin@example.com", Pw)
    second = await login(client, "twin@example.com", Pw)
    assert first["access_token"] and second["access_token"]
    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": second["refresh_token"]}
    )
    assert refreshed.status_code == 200
    logged_out = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": second["refresh_token"]}
    )
    assert logged_out.status_code == 204
    assert await _row_count(session_maker) == 0


async def test_startup_purge_removes_old_rows_keeps_fresh(
    client: AsyncClient,
    add_user: Callable[..., Awaitable[User]],
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Task 1.3: replay rows older than the retention window are deleted at startup."""
    user = await add_user("old@example.com", password=Pw, roles=["driver"])
    old_key = "c3c4c5c6-0000-4000-8000-000000000003"
    fresh_key = "c3c4c5c6-0000-4000-8000-000000000004"
    async with session_maker() as session:
        session.add_all(
            [
                IdempotencyKey(
                    user_id=user.id,
                    key=old_key,
                    request_hash="0" * 64,
                    response={"status": 201, "body": {}},
                    created_at=utcnow() - timedelta(days=RETENTION_DAYS + 1),
                ),
                IdempotencyKey(
                    user_id=user.id,
                    key=fresh_key,
                    request_hash="1" * 64,
                    response={"status": 201, "body": {}},
                    created_at=utcnow() - timedelta(days=1),
                ),
            ]
        )
        await session.commit()

    assert await purge_stale_idempotency_keys(session_maker) == 1
    assert await _row_count(session_maker) == 1
    async with session_maker() as session:
        remaining = (
            (await session.execute(select(IdempotencyKey).where(IdempotencyKey.user_id == user.id)))
            .scalars()
            .all()
        )
    assert [row.key for row in remaining] == [fresh_key]
