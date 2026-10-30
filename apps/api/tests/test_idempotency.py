"""Idempotency-Key middleware behaviour (constraint 4, offline replay)."""

from collections.abc import Awaitable, Callable
from typing import Any

from conftest import bearer, login
from httpx import AsyncClient

from app.models import User

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
    group_id = (await client.post("/api/v1/groups", json={"name": "A"}, headers=admin)).json()["id"]
    disp_id = (await client.get("/api/v1/auth/me", headers=disp)).json()["id"]
    assert (
        await client.put(f"/api/v1/groups/{group_id}/members/{disp_id}", headers=admin)
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
    group_id = (await client.post("/api/v1/groups", json={"name": "A"}, headers=admin)).json()["id"]
    disp = await _dispatcher_headers(client, add_user)
    disp_id = (await client.get("/api/v1/auth/me", headers=disp)).json()["id"]
    assert (
        await client.put(f"/api/v1/groups/{group_id}/members/{disp_id}", headers=admin)
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
