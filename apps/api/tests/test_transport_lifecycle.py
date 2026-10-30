"""API tests for the transport-lifecycle capability (mvp1-transports-and-orders)."""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from conftest import bearer, idem, login
from httpx import AsyncClient
from sqlalchemy import select

from app.models import TransportEvent, User

Pw = "secret123"


async def _tokens(client: AsyncClient, email: str) -> dict[str, str]:
    return bearer((await login(client, email, Pw))["access_token"])


class Fx:
    admin: dict[str, str] = {}
    disp: dict[str, str] = {}
    group_a: str = ""
    group_b: str = ""
    drv1: dict[str, str] = {}
    drv1_id: str = ""
    drv2: dict[str, str] = {}
    drv2_id: str = ""
    drv3: dict[str, str] = {}
    drv3_id: str = ""


async def setup(client: AsyncClient, add_user: Callable[..., Awaitable[User]]) -> Fx:
    fx = Fx()
    await add_user("boss@example.com", password=Pw, roles=["company-admin"], name="Boss")
    fx.admin = await _tokens(client, "boss@example.com")
    await add_user("disp@example.com", password=Pw, roles=["dispatcher"], name="Disp")
    fx.disp = await _tokens(client, "disp@example.com")
    disp_id = (await client.get("/api/v1/auth/me", headers=fx.disp)).json()["id"]
    for i in (1, 2, 3):
        await add_user(f"drv{i}@example.com", password=Pw, roles=["driver"], name=f"Drv{i}")
        h = await _tokens(client, f"drv{i}@example.com")
        uid = (await client.get("/api/v1/auth/me", headers=h)).json()["id"]
        setattr(fx, f"drv{i}", h)
        setattr(fx, f"drv{i}_id", uid)
    created = await client.post(
        "/api/v1/groups", json={"name": "A"}, headers={**fx.admin, **idem()}
    )
    fx.group_a = created.json()["id"]
    fx.group_b = (
        await client.post("/api/v1/groups", json={"name": "B"}, headers={**fx.admin, **idem()})
    ).json()["id"]
    assert (
        await client.put(
            f"/api/v1/groups/{fx.group_a}/members/{disp_id}", headers={**fx.admin, **idem()}
        )
    ).status_code == 204
    for i in (1, 2, 3):
        moved = await client.put(
            f"/api/v1/drivers/{getattr(fx, f'drv{i}_id')}/group",
            json={"group_id": fx.group_a},
            headers={**fx.admin, **idem()},
        )
        assert moved.status_code == 200, moved.text
    return fx


def _order_payload(group_id: str, number: str, **over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
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
    body.update(over)
    return body


async def _create_order(
    client: AsyncClient, headers: dict, group_id: str, number: str, **over: Any
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/orders",
        json=_order_payload(group_id, number, **over),
        headers={**headers, **idem()},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_transport(
    client: AsyncClient, headers: dict, order_id: str, **over: Any
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/transports", json={"order_id": order_id, **over}, headers={**headers, **idem()}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _assign(client: AsyncClient, headers: dict, tid: str, driver_ids: list[str]) -> Any:
    return await client.put(
        f"/api/v1/transports/{tid}/drivers",
        json={"driver_ids": driver_ids},
        headers={**headers, **idem()},
    )


async def _transition(client: AsyncClient, headers: dict, tid: str, event: str) -> Any:
    return await client.post(
        f"/api/v1/transports/{tid}/transitions",
        json={"event": event},
        headers={**headers, **idem()},
    )


async def _to_state(client: AsyncClient, fx: Fx, tid: str, target: str) -> None:
    """Drive a transport through the happy path with the assigned driver."""
    path = ["arrive_loading", "start_transit", "arrive_unloading", "finish_unloading"]
    for event in path:
        response = await _transition(client, fx.drv1, tid, event)
        assert response.status_code == 200, response.text
        if response.json()["state"] == target:
            return


async def test_state_machine_allowed_and_forbidden_transitions(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx = await setup(client, add_user)
    order = await _create_order(client, fx.disp, fx.group_a, "1")
    transport = await _create_transport(client, fx.disp, order["id"])
    assert transport["state"] == "draft"

    # assigned: in-transit shortcut does not exist in the binding machine
    assert (await _assign(client, fx.disp, transport["id"], [fx.drv1_id])).status_code == 200
    detail = await client.get(f"/api/v1/transports/{transport['id']}", headers=fx.drv1)
    assert detail.json()["state"] == "assigned"
    forbidden = await _transition(client, fx.drv1, transport["id"], "start_transit")
    assert forbidden.status_code == 409

    started = await _transition(client, fx.drv1, transport["id"], "arrive_loading")
    assert started.status_code == 200, started.text
    assert started.json()["state"] == "at_loading"
    assert (await _transition(client, fx.drv1, transport["id"], "start_transit")).json()[
        "state"
    ] == "in_transit"
    assert (await _transition(client, fx.drv1, transport["id"], "arrive_unloading")).json()[
        "state"
    ] == "at_unloading"
    done = await _transition(client, fx.drv1, transport["id"], "finish_unloading")
    assert done.json()["state"] == "completed"
    assert done.json()["completed_at"] is not None
    assert (await _transition(client, fx.drv1, transport["id"], "hand_in_documents")).json()[
        "state"
    ] == "in_review"
    accepted = await _transition(client, fx.disp, transport["id"], "accept")
    assert accepted.json()["state"] == "ready_for_invoicing"

    # a foreign driver cannot act
    other = await _transition(client, fx.drv2, transport["id"], "arrive_loading")
    assert other.status_code == 403
    # reopening is forbidden
    reopen = await _transition(client, fx.drv1, transport["id"], "finish_unloading")
    assert reopen.status_code == 409

    history = await client.get(f"/api/v1/transports/{transport['id']}/history", headers=fx.disp)
    assert history.status_code == 200
    events = history.json()
    state_events = [e for e in events if e["event_type"] == "state_change"]
    assert len(state_events) == 7
    assert [e["to_state"] for e in state_events] == [
        "assigned",
        "at_loading",
        "in_transit",
        "at_unloading",
        "completed",
        "in_review",
        "ready_for_invoicing",
    ]


async def test_third_driver_rejected(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx = await setup(client, add_user)
    order = await _create_order(client, fx.disp, fx.group_a, "1")
    transport = await _create_transport(client, fx.disp, order["id"])
    assert (
        await _assign(client, fx.disp, transport["id"], [fx.drv1_id, fx.drv2_id])
    ).status_code == 200
    third = await _assign(client, fx.disp, transport["id"], [fx.drv1_id, fx.drv2_id, fx.drv3_id])
    assert third.status_code == 422
    unchanged = await client.get(f"/api/v1/transports/{transport['id']}", headers=fx.disp)
    assert set(unchanged.json()["driver_ids"]) == {fx.drv1_id, fx.drv2_id}


async def test_driver_swap_during_ride(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx = await setup(client, add_user)
    order = await _create_order(client, fx.disp, fx.group_a, "1")
    transport = await _create_transport(client, fx.disp, order["id"])
    await _assign(client, fx.disp, transport["id"], [fx.drv1_id])
    await _to_state(client, fx, transport["id"], "in_transit")

    swapped = await _assign(client, fx.disp, transport["id"], [fx.drv2_id])
    assert swapped.status_code == 200, swapped.text
    assert swapped.json()["driver_ids"] == [fx.drv2_id]

    active_b = (await client.get("/api/v1/transports", headers=fx.drv2)).json()
    active_a = (await client.get("/api/v1/transports", headers=fx.drv1)).json()
    assert [t["id"] for t in active_b] == [transport["id"]]
    assert active_a == []
    assert (
        await _transition(client, fx.drv2, transport["id"], "arrive_unloading")
    ).status_code == 200

    history = (
        await client.get(f"/api/v1/transports/{transport['id']}/history", headers=fx.disp)
    ).json()
    assignment_events = [e for e in history if e["event_type"] == "assignment"]
    assert any(
        e["payload"]["added"] == [fx.drv2_id] and e["payload"]["removed"] == [fx.drv1_id]
        for e in assignment_events
    )


async def test_two_transports_transition_independently(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx = await setup(client, add_user)
    order = await _create_order(client, fx.disp, fx.group_a, "1")
    t1 = await _create_transport(client, fx.disp, order["id"])
    t2 = await _create_transport(client, fx.disp, order["id"])
    await _assign(client, fx.disp, t1["id"], [fx.drv1_id])
    await _assign(client, fx.disp, t2["id"], [fx.drv2_id])
    assert (await _transition(client, fx.drv1, t1["id"], "arrive_loading")).json()[
        "state"
    ] == "at_loading"
    untouched = await client.get(f"/api/v1/transports/{t2['id']}", headers=fx.disp)
    assert untouched.json()["state"] == "assigned"


async def test_cancel_order_cascade(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]], session_maker: Any
) -> None:
    fx = await setup(client, add_user)
    order = await _create_order(client, fx.disp, fx.group_a, "1")
    t_assigned = await _create_transport(client, fx.disp, order["id"])
    await _assign(client, fx.disp, t_assigned["id"], [fx.drv1_id])
    t_transit = await _create_transport(client, fx.disp, order["id"])
    await _assign(client, fx.disp, t_transit["id"], [fx.drv1_id])
    await _to_state(client, fx, t_transit["id"], "in_transit")
    t_done = await _create_transport(client, fx.disp, order["id"])
    await _assign(client, fx.disp, t_done["id"], [fx.drv1_id])
    await _to_state(client, fx, t_done["id"], "completed")

    cancelled = await client.post(
        f"/api/v1/orders/{order['id']}/cancel", headers={**fx.disp, **idem()}
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["cancelled_at"] is not None

    for tid, expected in (
        (t_assigned["id"], "cancelled"),
        (t_transit["id"], "cancelled"),
        (t_done["id"], "completed"),
    ):
        state = (await client.get(f"/api/v1/transports/{tid}", headers=fx.disp)).json()["state"]
        assert state == expected, (tid, state)

    # terminal: cancelled transports are inert
    inert = await _transition(client, fx.drv1, t_assigned["id"], "arrive_loading")
    assert inert.status_code == 409
    inert_assign = await _assign(client, fx.disp, t_assigned["id"], [fx.drv2_id])
    assert inert_assign.status_code == 409
    # cancelled order cannot gain transports; second cancel rejected
    assert (
        await client.post(
            "/api/v1/transports", json={"order_id": order["id"]}, headers={**fx.disp, **idem()}
        )
    ).status_code == 409
    again = await client.post(f"/api/v1/orders/{order['id']}/cancel", headers={**fx.disp, **idem()})
    assert again.status_code == 409

    history = (
        await client.get(f"/api/v1/transports/{t_transit['id']}/history", headers=fx.disp)
    ).json()
    assert history[-1]["to_state"] == "cancelled"
    async with session_maker() as session:
        order_events = (
            (
                await session.execute(
                    select(TransportEvent).where(
                        TransportEvent.order_id == uuid.UUID(order["id"]),
                        TransportEvent.event_type == "note",
                    )
                )
            )
            .scalars()
            .all()
        )
    assert any(e.payload.get("action") == "order_cancelled" for e in order_events)


async def test_order_currency_defaults_and_validation(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx = await setup(client, add_user)
    plain = await _create_order(client, fx.disp, fx.group_a, "1")
    assert plain["currency"] == "CZK"
    assert float(plain["price_total"]) == 6250.0

    eur = await _create_order(client, fx.disp, fx.group_a, "2", currency="EUR")
    assert eur["currency"] == "EUR"

    bad = await client.post(
        "/api/v1/orders",
        json=_order_payload(fx.group_a, "3", currency="USD"),
        headers={**fx.disp, **idem()},
    )
    assert bad.status_code == 422

    changed = await client.put(
        "/api/v1/settings", json={"default_currency": "EUR"}, headers={**fx.disp, **idem()}
    )
    assert changed.status_code == 200
    assert changed.json() == {"default_currency": "EUR"}
    defaulted = await _create_order(client, fx.disp, fx.group_a, "4")
    assert defaulted["currency"] == "EUR"

    invalid_setting = await client.put(
        "/api/v1/settings", json={"default_currency": "USD"}, headers={**fx.disp, **idem()}
    )
    assert invalid_setting.status_code == 422
    served = await client.get("/api/v1/settings", headers=fx.disp)
    assert served.json() == {"default_currency": "EUR"}


async def test_missing_billing_data_rejected(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx = await setup(client, add_user)
    body = _order_payload(fx.group_a, "1")
    del body["unit_price"], body["vat_rate"]
    response = await client.post("/api/v1/orders", json=body, headers={**fx.disp, **idem()})
    assert response.status_code == 422
    fields = {err["loc"][-1] for err in response.json()["detail"]}
    assert {"unit_price", "vat_rate"} <= fields


async def test_order_edit_logged(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]], session_maker: Any
) -> None:
    fx = await setup(client, add_user)
    order = await _create_order(client, fx.disp, fx.group_a, "1")
    edited = await client.patch(
        f"/api/v1/orders/{order['id']}",
        json={"unit_price": "600.00"},
        headers={**fx.disp, **idem()},
    )
    assert edited.status_code == 200, edited.text
    assert float(edited.json()["price_total"]) == 7500.0
    async with session_maker() as session:
        events = (
            (
                await session.execute(
                    select(TransportEvent).where(TransportEvent.order_id == uuid.UUID(order["id"]))
                )
            )
            .scalars()
            .all()
        )
    assert len(events) == 1
    assert events[0].payload == {"action": "order_updated", "changed": ["unit_price"]}


async def test_cross_group_order_as_if_absent(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx = await setup(client, add_user)
    b_order = await _create_order(client, fx.admin, fx.group_b, "B1")
    hidden = await client.get(f"/api/v1/orders/{b_order['id']}", headers=fx.disp)
    assert hidden.status_code == 404
    listed = (await client.get("/api/v1/orders", headers=fx.disp)).json()
    assert [o["id"] for o in listed] == []
