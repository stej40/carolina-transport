from collections.abc import Awaitable, Callable

from conftest import bearer, idem, login
from httpx import AsyncClient, Response

from app.models import User

PASSWORD = "secret123"


async def _login_as(
    client: AsyncClient,
    add_user: Callable[..., Awaitable[User]],
    email: str,
    roles: list[str],
    name: str = "Tester",
) -> tuple[dict[str, str], User]:
    user = await add_user(email, password=PASSWORD, roles=roles, name=name)
    tokens = await login(client, user.email, PASSWORD)
    return bearer(tokens["access_token"]), user


async def _group(client: AsyncClient, admin: dict[str, str], name: str) -> str:
    resp = await client.post("/api/v1/groups", json={"name": name}, headers={**admin, **idem()})
    assert resp.status_code == 201, resp.text
    gid: str = resp.json()["id"]
    return gid


async def _member(client: AsyncClient, admin: dict[str, str], gid: str, uid: str) -> None:
    resp = await client.put(f"/api/v1/groups/{gid}/members/{uid}", headers={**admin, **idem()})
    assert resp.status_code == 204, resp.text


async def _create(client: AsyncClient, admin: dict[str, str], email: str, roles: list[str]) -> str:
    resp = await client.post(
        "/api/v1/users",
        json={"email": email, "name": email.split("@")[0], "password": PASSWORD, "roles": roles},
        headers={**admin, **idem()},
    )
    assert resp.status_code == 201, resp.text
    uid: str = resp.json()["id"]
    return uid


async def _put_roles(
    client: AsyncClient,
    headers: dict[str, str],
    uid: str,
    roles: list[str],
    group_id: str | None = None,
    key: dict[str, str] | None = None,
) -> Response:
    body: dict[str, object] = {"roles": roles}
    if group_id is not None:
        body["group_id"] = group_id
    return await client.put(
        f"/api/v1/users/{uid}/roles",
        json=body,
        headers={**headers, **(key or idem())},
    )


async def test_dispatcher_grants_driver_to_roless_member_of_own_group(
    client: AsyncClient,
    add_user: Callable[..., Awaitable[User]],
) -> None:
    admin, _ = await _login_as(client, add_user, "admin1@x.cz", ["company-admin"])
    gid = await _group(client, admin, "G1")
    target = await _create(client, admin, "t1@x.cz", ["driver"])
    stripped = await _put_roles(client, admin, target, [], group_id=gid)
    assert stripped.status_code == 200, stripped.text
    assert stripped.json()["roles"] == []

    disp_h, disp = await _login_as(client, add_user, email="d1@x.cz", roles=["dispatcher"])
    await _member(client, admin, gid, str(disp.id))
    granted = await _put_roles(client, disp_h, target, ["driver"])
    assert granted.status_code == 200, granted.text
    assert granted.json()["roles"] == ["driver"]


async def test_dispatcher_rejects_out_of_scope_target(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    admin, _ = await _login_as(client, add_user, email="admin2@x.cz", roles=["company-admin"])
    g_a = await _group(client, admin, "A")
    g_b = await _group(client, admin, "B")
    target = await _create(client, admin, "t2@x.cz", ["driver"])
    await _put_roles(client, admin, target, [], group_id=g_b)

    disp_h, disp = await _login_as(client, add_user, email="d2@x.cz", roles=["dispatcher"])
    await _member(client, admin, g_a, str(disp.id))
    denied = await _put_roles(client, disp_h, target, ["driver"])
    assert denied.status_code == 403, denied.text
    assert "group scope" in denied.json()["detail"]
    still = await client.get("/api/v1/users", headers=disp_h)
    user = next(u for u in still.json() if u["id"] == target)
    assert user["roles"] == []


async def test_dispatcher_cannot_grant_dispatcher(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    admin, _ = await _login_as(client, add_user, email="admin3@x.cz", roles=["company-admin"])
    gid = await _group(client, admin, "G3")
    target = await _create(client, admin, "t3@x.cz", ["driver"])
    await _put_roles(client, admin, target, [], group_id=gid)

    disp_h, disp = await _login_as(client, add_user, email="d3@x.cz", roles=["dispatcher"])
    await _member(client, admin, gid, str(disp.id))
    denied = await _put_roles(client, disp_h, target, ["dispatcher"])
    assert denied.status_code == 403, denied.text


async def test_dispatcher_cannot_touch_dispatcher_account(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    admin, _ = await _login_as(client, add_user, email="admin4@x.cz", roles=["company-admin"])
    gid = await _group(client, admin, "G4")
    other_disp = await _create(client, admin, "d4b@x.cz", ["dispatcher"])
    await _put_roles(client, admin, other_disp, ["dispatcher"], group_id=gid)

    disp_h, disp = await _login_as(client, add_user, email="d4@x.cz", roles=["dispatcher"])
    await _member(client, admin, gid, str(disp.id))
    denied = await _put_roles(client, disp_h, other_disp, ["dispatcher", "driver"])
    assert denied.status_code == 403, denied.text


async def test_company_admin_grants_dispatcher(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    admin, _ = await _login_as(client, add_user, email="admin5@x.cz", roles=["company-admin"])
    target = await _create(client, admin, "t5@x.cz", ["driver"])
    resp = await _put_roles(client, admin, target, ["dispatcher"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["roles"] == ["dispatcher"]


async def test_company_admin_cannot_grant_admin_roles(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    admin, _ = await _login_as(client, add_user, email="admin6@x.cz", roles=["company-admin"])
    target = await _create(client, admin, "t6@x.cz", ["driver"])
    for role in ("company-admin", "system-admin"):
        denied = await _put_roles(client, admin, target, ["driver", role])
        assert denied.status_code == 403, denied.text


async def test_system_admin_grants_system_admin(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    sys_h, sys_user = await _login_as(
        client, add_user, email="root1@x.cz", roles=["system-admin"], name="Root"
    )
    target = await _create(client, sys_h, "t7@x.cz", ["driver"])
    assert str(sys_user.id) != target
    granted = await _put_roles(client, sys_h, target, ["system-admin"])
    assert granted.status_code == 200, granted.text
    assert granted.json()["roles"] == ["system-admin"]


async def test_self_change_rejected(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    admin, me = await _login_as(client, add_user, email="admin8@x.cz", roles=["company-admin"])
    denied = await _put_roles(client, admin, str(me.id), ["dispatcher"])
    assert denied.status_code == 403, denied.text
    assert "own roles" in denied.json()["detail"]


async def test_invalid_role_name_422(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    admin, _ = await _login_as(client, add_user, email="admin9@x.cz", roles=["company-admin"])
    target = await _create(client, admin, "t9@x.cz", ["driver"])
    resp = await _put_roles(client, admin, target, ["wizard"])
    assert resp.status_code == 422, resp.text


async def test_deactivated_target_404(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    admin, _ = await _login_as(client, add_user, email="admin10@x.cz", roles=["company-admin"])
    target = await _create(client, admin, "t10@x.cz", ["driver"])
    off = await client.post(f"/api/v1/users/{target}/deactivate", headers={**admin, **idem()})
    assert off.status_code == 200, off.text
    resp = await _put_roles(client, admin, target, [])
    assert resp.status_code == 404, resp.text


async def test_idempotent_replay(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    admin, _ = await _login_as(client, add_user, email="admin11@x.cz", roles=["company-admin"])
    gid = await _group(client, admin, "G11")
    target = await _create(client, admin, "t11@x.cz", ["driver"])
    await _put_roles(client, admin, target, [], group_id=gid)

    disp_h, disp = await _login_as(client, add_user, email="d11@x.cz", roles=["dispatcher"])
    await _member(client, admin, gid, str(disp.id))

    key = idem()
    first = await _put_roles(client, disp_h, target, ["driver"], key=key)
    replay = await _put_roles(client, disp_h, target, ["driver"], key=key)
    assert first.status_code == 200 and replay.status_code == 200, (first.text, replay.text)
    assert first.json() == replay.json()
    assert first.json()["roles"] == ["driver"]


async def test_lone_system_admin_cannot_self_deactivate(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    sys_h, sys_user = await _login_as(
        client, add_user, email="root12@x.cz", roles=["system-admin"], name="Root12"
    )
    denied = await client.post(
        f"/api/v1/users/{sys_user.id}/deactivate", headers={**sys_h, **idem()}
    )
    assert denied.status_code == 409, denied.text
    assert "system-admin" in denied.json()["detail"]


async def test_deactivation_ok_when_second_system_admin_exists(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    sys_h, first = await _login_as(
        client, add_user, email="root13@x.cz", roles=["system-admin"], name="Root13"
    )
    second = await _create(client, sys_h, "root13b@x.cz", ["system-admin"])
    assert second != str(first.id)
    resp = await client.post(f"/api/v1/users/{second}/deactivate", headers={**sys_h, **idem()})
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is False
    # deactivating the second leaves `first` as the last active admin,
    # so a following self-deactivation is now lockout-protected
    self_off = await client.post(
        f"/api/v1/users/{first.id}/deactivate", headers={**sys_h, **idem()}
    )
    assert self_off.status_code == 409, self_off.text


async def test_dispatcher_without_membership_rejected(
    client: AsyncClient, add_user: Callable[..., Awaitable[User]]
) -> None:
    admin, _ = await _login_as(client, add_user, "admin14@x.cz", ["company-admin"])
    gid = await _group(client, admin, "G14")
    target = await _create(client, admin, "t14@x.cz", ["driver"])
    await _put_roles(client, admin, target, [], group_id=gid)
    disp_h, _ = await _login_as(client, add_user, "d14@x.cz", ["dispatcher"])
    denied = await _put_roles(client, disp_h, target, ["driver"])
    assert denied.status_code == 403, denied.text
    assert "group scope" in denied.json()["detail"]
