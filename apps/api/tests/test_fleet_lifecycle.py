"""API tests for the fleet-retirement-unassignment change (retire/restore/unassign)."""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from conftest import idem
from httpx import AsyncClient
from test_organizational_groups import Fixture, setup
from test_transport_lifecycle import _create_order

from app.models import User


async def _register(
    client: AsyncClient, headers: dict, kind: str, group_id: str, spz: str
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/{kind}", json={"spz": spz, "group_id": group_id}, headers={**headers, **idem()}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _listing(client: AsyncClient, headers: dict, kind: str, query: str = "") -> list[dict]:
    response = await client.get(f"/api/v1/{kind}{query}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_dispatcher_cannot_register_retire_restore_or_unassign(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx: Fixture = await setup(client, add_user)
    truck = await _register(client, fx.admin, "trucks", fx.group_a, "1UM 2744")

    denied = await client.post(
        "/api/v1/trucks",
        json={"spz": "9H1 7475", "group_id": fx.group_a},
        headers={**fx.d1, **idem()},
    )
    assert denied.status_code == 403
    denied_trailers = await client.post(
        "/api/v1/trailers",
        json={"spz": "2SF 8619", "group_id": fx.group_a},
        headers={**fx.d1, **idem()},
    )
    assert denied_trailers.status_code == 403
    assert [t["id"] for t in await _listing(client, fx.admin, "trucks")] == [truck["id"]]

    for method, url in (
        ("delete", f"/api/v1/trucks/{truck['id']}"),
        ("delete", f"/api/v1/trucks/{truck['id']}/group"),
    ):
        response = await getattr(client, method)(url, headers={**fx.d1, **idem()})
        assert response.status_code == 403, response.text
    response = await client.post(
        f"/api/v1/trucks/{truck['id']}/restore", headers={**fx.d1, **idem()}
    )
    assert response.status_code == 403


async def test_retire_hides_and_restore_round_trip(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx: Fixture = await setup(client, add_user)
    truck = await _register(client, fx.admin, "trucks", fx.group_a, "1UM 2744")

    retired = await client.delete(f"/api/v1/trucks/{truck['id']}", headers={**fx.admin, **idem()})
    assert retired.status_code == 204
    # silent 204 on replay (retiring a retired row)
    replay = await client.delete(f"/api/v1/trucks/{truck['id']}", headers={**fx.admin, **idem()})
    assert replay.status_code == 204

    # hidden from dispatcher and default listings, kept row visible to admins
    assert await _listing(client, fx.d1, "trucks") == []
    assert await _listing(client, fx.admin, "trucks") == []
    with_retired = await _listing(client, fx.admin, "trucks", "?include_retired=true")
    assert [t["id"] for t in with_retired] == [truck["id"]]
    assert with_retired[0]["retired_at"] is not None
    # include_retired is admin-only
    denied = await client.get("/api/v1/trucks?include_retired=true", headers=fx.d1)
    assert denied.status_code == 403

    # SPZ freed for re-registration while the retired row stays retired
    twin = await _register(client, fx.admin, "trucks", fx.group_a, "1um  2744")
    assert twin["id"] != truck["id"]

    # restore conflicts while the SPZ is in active use
    conflict = await client.post(
        f"/api/v1/trucks/{truck['id']}/restore", headers={**fx.admin, **idem()}
    )
    assert conflict.status_code == 409
    rows = (await client.get("/api/v1/trucks?include_retired=true", headers=fx.admin)).json()
    assert {t["id"] for t in rows} == {truck["id"], twin["id"]}
    assert next(t for t in rows if t["id"] == truck["id"])["retired_at"] is not None

    # retire the twin, then restore the original
    assert (
        await client.delete(f"/api/v1/trucks/{twin['id']}", headers={**fx.admin, **idem()})
    ).status_code == 204
    restored = await client.post(
        f"/api/v1/trucks/{truck['id']}/restore", headers={**fx.admin, **idem()}
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["retired_at"] is None
    assert [t["id"] for t in await _listing(client, fx.d1, "trucks")] == [truck["id"]]
    # restoring an active vehicle is a replay-safe no-op
    again = await client.post(
        f"/api/v1/trucks/{truck['id']}/restore", headers={**fx.admin, **idem()}
    )
    assert again.status_code == 200
    assert again.json()["retired_at"] is None


async def test_duplicate_active_spz_still_conflicts(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx: Fixture = await setup(client, add_user)
    await _register(client, fx.admin, "trucks", fx.group_a, "1UM 2744")
    dup = await client.post(
        "/api/v1/trucks",
        json={"spz": "1um 2744", "group_id": fx.group_a},
        headers={**fx.admin, **idem()},
    )
    assert dup.status_code == 409
    trailer = await _register(client, fx.admin, "trailers", fx.group_a, "2SF 8619")
    retired = await client.delete(
        f"/api/v1/trailers/{trailer['id']}", headers={**fx.sysadmin, **idem()}
    )
    assert retired.status_code == 204
    assert (
        await client.post(
            "/api/v1/trailers",
            json={"spz": "2SF 8619", "group_id": fx.group_b},
            headers={**fx.sysadmin, **idem()},
        )
    ).status_code == 201


async def test_unassign_visibility_and_reassignment(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx: Fixture = await setup(client, add_user)
    truck = await _register(client, fx.admin, "trucks", fx.group_a, "1UM 2744")

    unassigned = await client.delete(
        f"/api/v1/trucks/{truck['id']}/group", headers={**fx.admin, **idem()}
    )
    assert unassigned.status_code == 204
    # replay-safe
    assert (
        await client.delete(f"/api/v1/trucks/{truck['id']}/group", headers={**fx.admin, **idem()})
    ).status_code == 204

    # invisible to group dispatchers, visible to admins with group_id null
    assert await _listing(client, fx.d1, "trucks") == []
    admin_rows = await _listing(client, fx.admin, "trucks")
    assert [t["id"] for t in admin_rows] == [truck["id"]]
    assert admin_rows[0]["group_id"] is None

    # admins reassign an unassigned vehicle via the existing move endpoint
    moved = await client.patch(
        f"/api/v1/trucks/{truck['id']}/group",
        json={"group_id": fx.group_b},
        headers={**fx.sysadmin, **idem()},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["group_id"] == fx.group_b

    # a dispatcher cannot address the unassigned row directly
    hidden = await client.patch(
        f"/api/v1/trucks/{truck['id']}/group",
        json={"group_id": fx.group_a},
        headers={**fx.d1, **idem()},
    )
    assert hidden.status_code == 404


async def test_move_retired_vehicle_is_404(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx: Fixture = await setup(client, add_user)
    truck = await _register(client, fx.admin, "trucks", fx.group_a, "1UM 2744")
    assert (
        await client.delete(f"/api/v1/trucks/{truck['id']}", headers={**fx.admin, **idem()})
    ).status_code == 204

    moved = await client.patch(
        f"/api/v1/trucks/{truck['id']}/group",
        json={"group_id": fx.group_b},
        headers={**fx.admin, **idem()},
    )
    assert moved.status_code == 404
    unassigned = await client.delete(
        f"/api/v1/trucks/{truck['id']}/group", headers={**fx.admin, **idem()}
    )
    assert unassigned.status_code == 404


async def test_transport_creation_rejects_retired_fleet(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx: Fixture = await setup(client, add_user)
    order = await _create_order(client, fx.d1, fx.group_a, "O1")
    truck = await _register(client, fx.admin, "trucks", fx.group_a, "1UM 2744")
    trailer = await _register(client, fx.admin, "trailers", fx.group_a, "2SF 8619")

    created = await client.post(
        "/api/v1/transports",
        json={"order_id": order["id"], "truck_id": truck["id"], "trailer_id": trailer["id"]},
        headers={**fx.d1, **idem()},
    )
    assert created.status_code == 201, created.text

    assert (
        await client.delete(f"/api/v1/trucks/{truck['id']}", headers={**fx.admin, **idem()})
    ).status_code == 204

    # saved transport still renders the retired truck (history preserved)
    listed = await client.get(f"/api/v1/transports/{created.json()['id']}", headers=fx.d1)
    assert listed.status_code == 200
    assert listed.json()["truck_id"] == truck["id"]

    # new transports must not reference retired or unknown fleet
    rejected = await client.post(
        "/api/v1/transports",
        json={"order_id": order["id"], "truck_id": truck["id"]},
        headers={**fx.d1, **idem()},
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "Unknown truck or trailer"
    unknown = await client.post(
        "/api/v1/transports",
        json={"order_id": order["id"], "trailer_id": str(uuid.uuid4())},
        headers={**fx.d1, **idem()},
    )
    assert unknown.status_code == 400
    assert unknown.json()["detail"] == "Unknown truck or trailer"

    # active trailer still works
    ok = await client.post(
        "/api/v1/transports",
        json={"order_id": order["id"], "trailer_id": trailer["id"]},
        headers={**fx.d1, **idem()},
    )
    assert ok.status_code == 201, ok.text


async def test_label_editing(client: AsyncClient, add_user: Callable[..., Awaitable[User]]) -> None:
    fx: Fixture = await setup(client, add_user)
    truck = await _register(client, fx.admin, "trucks", fx.group_a, "1UM 2744")

    patched = await client.patch(
        f"/api/v1/trucks/{truck['id']}",
        json={"label": "Hvezda"},
        headers={**fx.d1, **idem()},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["label"] == "Hvezda"

    # any member of the group may relabel; a group-less body is a no-op
    d2_update = await client.patch(
        f"/api/v1/trucks/{truck['id']}",
        json={"label": "Kombajn"},
        headers={**fx.d2, **idem()},
    )
    assert d2_update.status_code == 200
    assert d2_update.json()["label"] == "Kombajn"
    noop = await client.patch(f"/api/v1/trucks/{truck['id']}", json={}, headers={**fx.d1, **idem()})
    assert noop.status_code == 200 and noop.json()["label"] == "Kombajn"

    # the label key may also clear the value
    cleared = await client.patch(
        f"/api/v1/trucks/{truck['id']}", json={"label": None}, headers={**fx.d1, **idem()}
    )
    assert cleared.status_code == 200 and cleared.json()["label"] is None

    # unassigned: invisible to dispatchers, admins may still relabel
    assert (
        await client.delete(f"/api/v1/trucks/{truck['id']}/group", headers={**fx.admin, **idem()})
    ).status_code == 204
    hidden = await client.patch(
        f"/api/v1/trucks/{truck['id']}",
        json={"label": "cizni"},
        headers={**fx.d1, **idem()},
    )
    assert hidden.status_code == 404
    admin_update = await client.patch(
        f"/api/v1/trucks/{truck['id']}",
        json={"label": "Sklad"},
        headers={**fx.admin, **idem()},
    )
    assert admin_update.status_code == 200 and admin_update.json()["label"] == "Sklad"

    # retired vehicles are not addressable for label editing
    assert (
        await client.delete(f"/api/v1/trucks/{truck['id']}", headers={**fx.admin, **idem()})
    ).status_code == 204
    retired = await client.patch(
        f"/api/v1/trucks/{truck['id']}",
        json={"label": "nope"},
        headers={**fx.admin, **idem()},
    )
    assert retired.status_code == 404
    rows = (await client.get("/api/v1/trucks?include_retired=true", headers=fx.admin)).json()
    assert next(r for r in rows if r["id"] == truck["id"])["label"] == "Sklad"
