"""API tests for the document-collection capability (mvp1-document-collection).

Garage/S3 is faked: presign returns deterministic URLs and object_exists
consults a set the test "uploads" into by adding the storage key.
"""

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from conftest import bearer, idem, login
from httpx import AsyncClient
from test_transport_lifecycle import _assign, _create_order, _create_transport, setup

import app.storage as app_storage

Pw = "secret123"

TICKET_FIELDS = [
    {"name": "ticket_number", "label": "Cislo", "required": True},
    {"name": "net_weight", "label": "Cista hmotnost", "required": True},
]
ORDER_FIELDS = [
    {"name": "number", "label": "Cislo", "required": True},
    {"name": "date", "label": "Datum", "required": True},
    {"name": "counterparty_name", "label": "Objednatel", "required": True},
]


@pytest.fixture
def objects(monkeypatch: pytest.MonkeyPatch) -> set[str]:
    uploaded: set[str] = set()
    monkeypatch.setattr(
        app_storage, "presign_put", lambda key, mime: f"https://garage.test/{key}?sig=put"
    )
    monkeypatch.setattr(
        app_storage, "presign_get", lambda key: f"https://garage.test/{key}?sig=get"
    )
    monkeypatch.setattr(app_storage, "object_exists", lambda key: key in uploaded)
    return uploaded


async def _tokens(client: AsyncClient, email: str) -> dict[str, str]:
    return bearer((await login(client, email, Pw))["access_token"])


async def _me(client: AsyncClient, headers: dict[str, str]) -> str:
    return (await client.get("/api/v1/auth/me", headers=headers)).json()["id"]


async def _create_type(
    client: AsyncClient,
    admin: dict[str, str],
    key: str,
    default_required: bool = False,
    variant: str = "none",
    fields: list[dict[str, Any]] | None = None,
) -> str:
    response = await client.post(
        "/api/v1/document-types",
        json={
            "key": key,
            "label_cs": key,
            "label_de": key,
            "variant": variant,
            "default_required": default_required,
            "attribute_schema": {"fields": fields or []},
        },
        headers={**admin, **idem()},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _taxonomy(client: AsyncClient, admin: dict[str, str]) -> dict[str, str]:
    types = {}
    types["transport_order"] = await _create_type(
        client, admin, "transport_order", default_required=True, fields=ORDER_FIELDS
    )
    types["cmr"] = await _create_type(client, admin, "cmr")
    types["weighbridge_ticket_loading"] = await _create_type(
        client,
        admin,
        "weighbridge_ticket_loading",
        variant="loading",
        fields=TICKET_FIELDS,
    )
    types["weighbridge_ticket_unloading"] = await _create_type(
        client,
        admin,
        "weighbridge_ticket_unloading",
        variant="unloading",
        fields=TICKET_FIELDS,
    )
    return types


async def _request_upload(
    client: AsyncClient, headers: dict[str, str], tid: str, type_id: str, **over: Any
) -> Any:
    return await client.post(
        f"/api/v1/transports/{tid}/documents",
        json={"document_type_id": type_id, "source": "photo", "mime": "image/jpeg", **over},
        headers={**headers, **idem()},
    )


async def _upload_and_confirm(
    client: AsyncClient, headers: dict[str, str], tid: str, type_id: str, objects: set[str]
) -> dict[str, Any]:
    created = await _request_upload(client, headers, tid, type_id)
    assert created.status_code == 201, created.text
    body = created.json()
    doc = body["document"]
    assert body["upload_url"] == f"https://garage.test/documents/{tid}/{doc['id']}/1?sig=put"
    assert doc["status"] == "draft"
    # confirm before the bytes are in storage must fail
    early = await client.post(
        f"/api/v1/documents/{doc['id']}/confirm", headers={**headers, **idem()}
    )
    assert early.status_code == 409
    objects.add(f"documents/{tid}/{doc['id']}/1")
    confirmed = await client.post(
        f"/api/v1/documents/{doc['id']}/confirm", headers={**headers, **idem()}
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "pending_review"
    return confirmed.json()


async def _enter(client: AsyncClient, headers: dict[str, str], doc_id: str, attributes: dict):
    return await client.patch(
        f"/api/v1/documents/{doc_id}/attributes",
        json={"attributes": attributes},
        headers={**headers, **idem()},
    )


async def _review(
    client: AsyncClient, headers: dict[str, str], doc_id: str, decision: str, reason: str | None
):
    return await client.post(
        f"/api/v1/documents/{doc_id}/review",
        json={"decision": decision, "reason": reason},
        headers={**headers, **idem()},
    )


async def _transport_view(client: AsyncClient, headers: dict[str, str], tid: str):
    return (await client.get(f"/api/v1/transports/{tid}", headers=headers)).json()


async def test_e2e_upload_to_pending_review_to_approved(
    client: AsyncClient,
    add_user: Callable[..., Awaitable[Any]],
    objects: set[str],
) -> None:
    fx = await setup(client, add_user)
    types = await _taxonomy(client, fx.admin)
    order = await _create_order(client, fx.disp, fx.group_a, "1")
    transport = await _create_transport(client, fx.disp, order["id"])
    await _assign(client, fx.disp, transport["id"], [fx.drv1_id])

    doc = await _upload_and_confirm(
        client, fx.drv1, transport["id"], types["transport_order"], objects
    )
    assert doc["created_by"] == fx.drv1_id

    # approving without the required attributes is refused
    too_early = await _review(client, fx.disp, doc["id"], "approve", None)
    assert too_early.status_code == 422
    assert "ticket" not in too_early.json()["detail"]

    entered = await _enter(
        client,
        fx.drv1,
        doc["id"],
        {"number": "2026001", "date": "2026-10-30", "counterparty_name": "Agro"},
    )
    assert entered.status_code == 200, entered.text
    approved = await _review(client, fx.disp, doc["id"], "approve", None)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "accepted"
    assert [r["decision"] for r in approved.json()["reviews"]] == ["approve"]

    view = await _transport_view(client, fx.disp, transport["id"])
    assert "transport_order" not in view["missing_documents"]

    # reviewers see the file: presigned download URL
    download = await client.get(f"/api/v1/documents/{doc['id']}/download", headers=fx.disp)
    assert download.status_code == 200
    assert download.json()["url"].startswith("https://garage.test/documents/")

    # accepted documents stay immutable
    assert (await _enter(client, fx.drv1, doc["id"], {"number": "x"})).status_code == 409


async def test_expired_presign_can_be_refreshed_by_uploader(
    client: AsyncClient,
    add_user: Callable[..., Awaitable[Any]],
    objects: set[str],
) -> None:
    fx = await setup(client, add_user)
    types = await _taxonomy(client, fx.admin)
    order = await _create_order(client, fx.disp, fx.group_a, "1")
    transport = await _create_transport(client, fx.disp, order["id"])
    await _assign(client, fx.disp, transport["id"], [fx.drv1_id])

    created = await _request_upload(client, fx.drv1, transport["id"], types["transport_order"])
    doc = created.json()["document"]

    # a dispatcher who is not the uploader cannot re-presign someone's draft
    foreign = await client.get(
        f"/api/v1/documents/{doc['id']}/upload-url",
        headers={**fx.disp, **idem()},
    )
    assert foreign.status_code == 403

    fresh = await client.get(f"/api/v1/documents/{doc['id']}/upload-url", headers=fx.drv1)
    assert fresh.status_code == 200, fresh.text
    assert (
        fresh.json()["upload_url"]
        == f"https://garage.test/documents/{transport['id']}/{doc['id']}/1?sig=put"
    )


async def test_driver_upload_to_unassigned_transport_rejected(
    client: AsyncClient,
    add_user: Callable[..., Awaitable[Any]],
    objects: set[str],
) -> None:
    fx = await setup(client, add_user)
    types = await _taxonomy(client, fx.admin)
    order = await _create_order(client, fx.disp, fx.group_a, "1")
    transport = await _create_transport(client, fx.disp, order["id"])
    await _assign(client, fx.disp, transport["id"], [fx.drv1_id])

    forbidden = await _request_upload(client, fx.drv2, transport["id"], types["transport_order"])
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "Driver is not assigned to this transport"

    # no draft row and no presigned url were created
    listed = await client.get(f"/api/v1/transports/{transport['id']}/documents", headers=fx.disp)
    assert listed.status_code == 200
    assert listed.json() == []


async def test_dispatcher_upload_on_in_transit_transport(
    client: AsyncClient,
    add_user: Callable[..., Awaitable[Any]],
    objects: set[str],
) -> None:
    fx = await setup(client, add_user)
    types = await _taxonomy(client, fx.admin)
    order = await _create_order(client, fx.disp, fx.group_a, "1")
    transport = await _create_transport(client, fx.disp, order["id"])
    await _assign(client, fx.disp, transport["id"], [fx.drv1_id])
    for event in ("arrive_loading", "start_transit"):
        moved = await client.post(
            f"/api/v1/transports/{transport['id']}/transitions",
            json={"event": event},
            headers={**fx.drv1, **idem()},
        )
        assert moved.status_code == 200, moved.text

    doc = await _upload_and_confirm(
        client, fx.disp, transport["id"], types["transport_order"], objects
    )
    assert doc["status"] == "pending_review"
    assert doc["created_by"] == await _me(client, fx.disp)


async def test_reject_resubmit_keeps_both_versions(
    client: AsyncClient,
    add_user: Callable[..., Awaitable[Any]],
    objects: set[str],
) -> None:
    fx = await setup(client, add_user)
    types = await _taxonomy(client, fx.admin)
    order = await _create_order(client, fx.disp, fx.group_a, "1")
    transport = await _create_transport(client, fx.disp, order["id"])
    await _assign(client, fx.disp, transport["id"], [fx.drv1_id])
    loading = types["weighbridge_ticket_loading"]

    v1 = await _upload_and_confirm(client, fx.drv1, transport["id"], loading, objects)
    await _enter(client, fx.drv1, v1["id"], {"ticket_number": "77", "net_weight": "10.2"})
    rejected = await _review(client, fx.disp, v1["id"], "reject", "blurry photo")
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["reviews"][0]["reason"] == "blurry photo"

    # rejection reason is mandatory
    no_reason = await _review(client, fx.disp, v1["id"], "reject", None)
    assert no_reason.status_code == 422

    # rejected doc now shows as missing again
    view = await _transport_view(client, fx.disp, transport["id"])
    assert "weighbridge_ticket_loading" in view["missing_documents"]

    resub = await _request_upload(
        client, fx.drv1, transport["id"], loading, resubmits_document_id=v1["id"]
    )
    assert resub.status_code == 201, resub.text
    v2 = resub.json()["document"]
    assert v2["version"] == 2
    assert v2["supersedes_id"] == v1["id"]
    assert resub.json()["upload_url"] == (
        f"https://garage.test/documents/{transport['id']}/{v2['id']}/2?sig=put"
    )

    # double resubmission of the same rejected version is refused
    again = await _request_upload(
        client, fx.drv1, transport["id"], loading, resubmits_document_id=v1["id"]
    )
    assert again.status_code == 409

    objects.add(f"documents/{transport['id']}/{v2['id']}/2")
    confirmed = await client.post(
        f"/api/v1/documents/{v2['id']}/confirm", headers={**fx.drv1, **idem()}
    )
    assert confirmed.json()["status"] == "pending_review"
    await _enter(client, fx.drv1, v2["id"], {"ticket_number": "77", "net_weight": "10.18"})
    approved = await _review(client, fx.disp, v2["id"], "approve", None)
    assert approved.json()["status"] == "accepted"

    history = await client.get(f"/api/v1/transports/{transport['id']}/documents", headers=fx.drv1)
    assert history.status_code == 200
    rows = history.json()
    by_version = {d["version"]: d for d in rows if d["document_type_id"] == loading}
    assert set(by_version) == {1, 2}
    assert by_version[1]["status"] == "rejected"
    assert by_version[2]["status"] == "accepted"
    assert by_version[2]["created_by"] == fx.drv1_id

    view = await _transport_view(client, fx.drv1, transport["id"])
    assert "weighbridge_ticket_loading" not in view["missing_documents"]


async def test_completeness_incomplete_until_required_approved(
    client: AsyncClient,
    add_user: Callable[..., Awaitable[Any]],
    objects: set[str],
) -> None:
    fx = await setup(client, add_user)
    types = await _taxonomy(client, fx.admin)
    # weight-priced domestic transport => transport_order + both weighbridge tickets
    order = await _create_order(client, fx.disp, fx.group_a, "1")
    transport = await _create_transport(client, fx.disp, order["id"])
    await _assign(client, fx.disp, transport["id"], [fx.drv1_id])

    view = await _transport_view(client, fx.drv1, transport["id"])
    assert not view["documents_complete"]
    assert view["missing_documents"] == [
        "transport_order",
        "weighbridge_ticket_loading",
        "weighbridge_ticket_unloading",
    ]

    loading = await _upload_and_confirm(
        client, fx.drv1, transport["id"], types["weighbridge_ticket_loading"], objects
    )
    await _enter(client, fx.drv1, loading["id"], {"ticket_number": "1", "net_weight": "10"})
    assert (await _review(client, fx.disp, loading["id"], "approve", None)).status_code == 200

    view = await _transport_view(client, fx.disp, transport["id"])
    assert view["missing_documents"] == [
        "transport_order",
        "weighbridge_ticket_unloading",
    ]

    # non-approved (draft or pending) versions do not count
    unloading = await _upload_and_confirm(
        client, fx.drv1, transport["id"], types["weighbridge_ticket_unloading"], objects
    )
    order_doc = await _upload_and_confirm(
        client, fx.disp, transport["id"], types["transport_order"], objects
    )
    await _enter(client, fx.drv1, unloading["id"], {"ticket_number": "2", "net_weight": "9.9"})
    await _enter(
        client,
        fx.disp,
        order_doc["id"],
        {"number": "2026001", "date": "2026-10-30", "counterparty_name": "Agro"},
    )
    for decision_doc in (unloading, order_doc):
        approved = await _review(client, fx.disp, decision_doc["id"], "approve", None)
        assert approved.status_code == 200, approved.text

    final = await _transport_view(client, fx.drv1, transport["id"])
    assert final["documents_complete"]
    assert final["missing_documents"] == []

    # the dashboard-style list exposes the same flags
    listed = (await client.get("/api/v1/transports", headers=fx.disp)).json()
    assert listed[0]["documents_complete"]

    # a domestic transport does not require CMR
    assert "cmr" not in final["missing_documents"]
