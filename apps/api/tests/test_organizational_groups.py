from collections.abc import Awaitable, Callable

from conftest import bearer, idem, login
from httpx import AsyncClient

from app.models import User

Pw = "secret123"


async def _tokens(client: AsyncClient, email: str) -> dict[str, str]:
    return bearer((await login(client, email, Pw))["access_token"])


async def _admin_headers(client: AsyncClient, add_user, role: str = "company-admin") -> dict:
    email = f"{role}@example.com"
    await add_user(email, password=Pw, roles=[role], name="Admin")
    return await _tokens(client, email)


async def _group_headers(client: AsyncClient, add_user, name: str) -> dict:
    email = f"{name}@example.com"
    await add_user(email, password=Pw, roles=["dispatcher"], name=name)
    return await _tokens(client, email)


async def _create_group(client: AsyncClient, headers: dict, name: str) -> str:
    response = await client.post(
        "/api/v1/groups", json={"name": name}, headers={**headers, **idem()}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


class Fixture:
    """company-admin, system-admin, two groups (A: dispatchers d1+d2, B: none)."""

    def __init__(self) -> None:
        self.admin: dict = {}
        self.sysadmin: dict = {}
        self.d1: dict = {}
        self.d2: dict = {}
        self.group_a = ""
        self.group_b = ""


async def setup(client: AsyncClient, add_user: Callable[..., Awaitable[User]]) -> Fixture:
    fx = Fixture()
    fx.admin = await _admin_headers(client, add_user, "company-admin")
    fx.sysadmin = await _admin_headers(client, add_user, "system-admin")
    fx.d1 = await _group_headers(client, add_user, "d1")
    fx.d2 = await _group_headers(client, add_user, "d2")
    d1_id = (await client.get("/api/v1/auth/me", headers=fx.d1)).json()["id"]
    d2_id = (await client.get("/api/v1/auth/me", headers=fx.d2)).json()["id"]
    fx.group_a = await _create_group(client, fx.admin, "A")
    fx.group_b = await _create_group(client, fx.admin, "B")
    for gid, uid in ((fx.group_a, d1_id), (fx.group_a, d2_id)):
        added = await client.put(
            f"/api/v1/groups/{gid}/members/{uid}", headers={**fx.admin, **idem()}
        )
        assert added.status_code == 204, added.text
    return fx


async def test_membership_matrix(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx = await setup(client, add_user)

    # group with multiple dispatchers: both see it; group with zero dispatchers exists
    d1_groups = (await client.get("/api/v1/groups", headers=fx.d1)).json()
    d2_groups = (await client.get("/api/v1/groups", headers=fx.d2)).json()
    assert [g["id"] for g in d1_groups] == [fx.group_a]
    assert [g["id"] for g in d2_groups] == [fx.group_a]

    # foreign group behaves as not-found
    foreign = await client.get(f"/api/v1/groups/{fx.group_b}", headers=fx.d1)
    assert foreign.status_code == 404
    # own group detail works
    assert (await client.get(f"/api/v1/groups/{fx.group_a}", headers=fx.d1)).status_code == 200

    # company-admin sees all groups incl. the dispatcher-less one
    admin_groups = (await client.get("/api/v1/groups", headers=fx.admin)).json()
    assert {g["id"] for g in admin_groups} == {fx.group_a, fx.group_b}

    # dispatchers cannot manage groups or memberships
    denied = await client.post("/api/v1/groups", json={"name": "C"}, headers={**fx.d1, **idem()})
    assert denied.status_code == 403
    driver_email = "drv@example.com"
    await add_user(driver_email, password=Pw, roles=["driver"], name="Driver")
    me = await client.get("/api/v1/auth/me", headers=await _tokens(client, driver_email))
    driver_id = me.json()["id"]
    not_disp = await client.put(
        f"/api/v1/groups/{fx.group_a}/members/{driver_id}", headers={**fx.admin, **idem()}
    )
    assert not_disp.status_code == 400


async def test_fleet_registration_and_scoping(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx = await setup(client, add_user)

    truck = await client.post(
        "/api/v1/trucks",
        json={"spz": "1um 2744", "group_id": fx.group_a},
        headers={**fx.d1, **idem()},
    )
    assert truck.status_code == 201, truck.text
    assert truck.json()["spz"] == "1UM 2744"
    trailer = await client.post(
        "/api/v1/trailers",
        json={"spz": "2SF 8619", "group_id": fx.group_a},
        headers={**fx.d1, **idem()},
    )
    assert trailer.status_code == 201, trailer.text

    # duplicate SPZ rejected (scenario: trailer SPZ uniqueness)
    dup = await client.post(
        "/api/v1/trailers",
        json={"spz": "2sf  8619", "group_id": fx.group_a},
        headers={**fx.admin, **idem()},
    )
    assert dup.status_code == 409

    # foreign group is not addressable for registration
    foreign = await client.post(
        "/api/v1/trucks",
        json={"spz": "9H1 7475", "group_id": fx.group_b},
        headers={**fx.d1, **idem()},
    )
    assert foreign.status_code == 404

    # scoped listings
    d1_trucks = (await client.get("/api/v1/trucks", headers=fx.d1)).json()
    admin_trucks = (await client.get("/api/v1/trucks", headers=fx.admin)).json()
    assert [t["id"] for t in d1_trucks] == [truck.json()["id"]]
    assert len(admin_trucks) == 1

    # company-admin registers into the dispatcher-less group B
    b_truck = await client.post(
        "/api/v1/trucks",
        json={"spz": "1UK 1283", "group_id": fx.group_b},
        headers={**fx.admin, **idem()},
    )
    assert b_truck.status_code == 201


async def test_moves_between_groups(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx = await setup(client, add_user)
    truck = (
        await client.post(
            "/api/v1/trucks",
            json={"spz": "1UM 2744", "group_id": fx.group_a},
            headers={**fx.d1, **idem()},
        )
    ).json()

    # dispatcher moves resource into a foreign group -> 403
    denied = await client.patch(
        f"/api/v1/trucks/{truck['id']}/group",
        json={"group_id": fx.group_b},
        headers={**fx.d1, **idem()},
    )
    assert denied.status_code == 403

    # dispatcher moves a foreign resource -> not-found
    b_truck = (
        await client.post(
            "/api/v1/trucks",
            json={"spz": "1UK 1283", "group_id": fx.group_b},
            headers={**fx.admin, **idem()},
        )
    ).json()
    hidden = await client.patch(
        f"/api/v1/trucks/{b_truck['id']}/group",
        json={"group_id": fx.group_a},
        headers={**fx.d1, **idem()},
    )
    assert hidden.status_code == 404

    # dispatcher move between two own groups is fine
    group_c = await _create_group(client, fx.admin, "C")
    d1_id = (await client.get("/api/v1/auth/me", headers=fx.d1)).json()["id"]
    assert (
        await client.put(
            f"/api/v1/groups/{group_c}/members/{d1_id}", headers={**fx.admin, **idem()}
        )
    ).status_code == 204
    moved = await client.patch(
        f"/api/v1/trucks/{truck['id']}/group",
        json={"group_id": group_c},
        headers={**fx.d1, **idem()},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["group_id"] == group_c

    # company-admin moves anywhere; system-admin unrestricted
    admin_move = await client.patch(
        f"/api/v1/trucks/{truck['id']}/group",
        json={"group_id": fx.group_b},
        headers={**fx.admin, **idem()},
    )
    assert admin_move.status_code == 200
    sys_move = await client.patch(
        f"/api/v1/trucks/{truck['id']}/group",
        json={"group_id": fx.group_a},
        headers={**fx.sysadmin, **idem()},
    )
    assert sys_move.status_code == 200

    # trailer move follows the same rules
    trailer = (
        await client.post(
            "/api/v1/trailers",
            json={"spz": "2SF 8619", "group_id": fx.group_a},
            headers={**fx.d1, **idem()},
        )
    ).json()
    trailer_move = await client.patch(
        f"/api/v1/trailers/{trailer['id']}/group",
        json={"group_id": group_c},
        headers={**fx.d1, **idem()},
    )
    assert trailer_move.status_code == 200


async def test_driver_group_assignment(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    fx = await setup(client, add_user)
    await add_user("drv1@example.com", password=Pw, roles=["driver"], name="Horcik")
    drv_me = await client.get("/api/v1/auth/me", headers=await _tokens(client, "drv1@example.com"))
    drv = drv_me.json()

    # company-admin assigns driver to any group
    assigned = await client.put(
        f"/api/v1/drivers/{drv['id']}/group",
        json={"group_id": fx.group_a},
        headers={**fx.admin, **idem()},
    )
    assert assigned.status_code == 200, assigned.text
    detail = (await client.get(f"/api/v1/groups/{fx.group_a}", headers=fx.admin)).json()
    assert [u["id"] for u in detail["drivers"]] == [drv["id"]]

    # dispatcher (member of A) moves the driver out to their second group C
    group_c = await _create_group(client, fx.admin, "C")
    d1_id = (await client.get("/api/v1/auth/me", headers=fx.d1)).json()["id"]
    assert (
        await client.put(
            f"/api/v1/groups/{group_c}/members/{d1_id}", headers={**fx.admin, **idem()}
        )
    ).status_code == 204
    moved = await client.put(
        f"/api/v1/drivers/{drv['id']}/group",
        json={"group_id": group_c},
        headers={**fx.d1, **idem()},
    )
    assert moved.status_code == 200
    assert moved.json()["group_id"] == group_c

    # d2 (member of A only) cannot touch a driver parked in C
    denied = await client.put(
        f"/api/v1/drivers/{drv['id']}/group",
        json={"group_id": fx.group_a},
        headers={**fx.d2, **idem()},
    )
    assert denied.status_code == 403

    # non-driver target rejected; system-admin may assign anywhere
    not_driver = await client.put(
        f"/api/v1/drivers/{d1_id}/group",
        json={"group_id": fx.group_a},
        headers={**fx.sysadmin, **idem()},
    )
    assert not_driver.status_code == 400
    sys_move = await client.put(
        f"/api/v1/drivers/{drv['id']}/group",
        json={"group_id": fx.group_b},
        headers={**fx.sysadmin, **idem()},
    )
    assert sys_move.status_code == 200
