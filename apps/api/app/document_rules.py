"""Which documents a transport requires, and whether its file is complete.

Completeness is computed, never stored (mvp1-document-collection design.md).
The conditional rules follow the signed discovery completeness rule
(mvp1-domain-discovery design.md §1): international => CMR, weight-priced
cargo => both weighbridge tickets. `cleaning_declaration` and `delivery_note`
have no order attribute to key off in MVP1, so they stay dispatcher-added
(default_required=false); `customs_document` is seeded inactive.
"""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DOC_STATUS_ACCEPTED, Document, DocumentType, Order, Transport

WEIGHT_UNITS = ("t", "kg")
WEIGHBRIDGE_KEYS = ("weighbridge_ticket_loading", "weighbridge_ticket_unloading")


def required_type_keys(
    types: Sequence[DocumentType], transport: Transport, order: Order | None
) -> set[str]:
    """Active document-type keys the transport's file must contain approved."""
    active = [t for t in types if t.is_active]
    keys = {t.key for t in active if t.default_required}
    known = {t.key for t in active}
    if transport.is_international:
        keys |= {"cmr"} & known
    if order is not None and order.unit.lower() in WEIGHT_UNITS:
        keys |= set(WEIGHBRIDGE_KEYS) & known
    return keys


def missing_required_attributes(doc_type: DocumentType, attributes: dict[str, Any]) -> list[str]:
    fields = (doc_type.attribute_schema or {}).get("fields", [])
    return [
        str(field["name"])
        for field in fields
        if field.get("required")
        and field.get("name")
        and not str(attributes.get(str(field["name"]), "")).strip()
    ]


async def missing_documents_for(
    session: AsyncSession, transports: Sequence[Transport]
) -> dict[uuid.UUID, list[str]]:
    """transport id -> required type keys lacking an approved current version.

    Superseded rows do not count as current; a rejected document therefore
    shows its type as missing until a corrected version is approved.
    """
    if not transports:
        return {}
    types = list((await session.execute(select(DocumentType))).scalars().all())
    order_ids = {t.order_id for t in transports}
    orders: dict[uuid.UUID, Order] = {}
    if order_ids:
        orders = {
            o.id: o
            for o in (await session.execute(select(Order).where(Order.id.in_(order_ids))))
            .scalars()
            .all()
        }
    transport_ids = [t.id for t in transports]
    docs = list(
        (await session.execute(select(Document).where(Document.transport_id.in_(transport_ids))))
        .scalars()
        .all()
    )
    superseded = {d.supersedes_id for d in docs if d.supersedes_id is not None}
    type_by_id = {t.id: t for t in types}
    approved_current: dict[uuid.UUID, set[str]] = {}
    for doc in docs:
        if doc.status != DOC_STATUS_ACCEPTED or doc.id in superseded:
            continue
        doc_type = type_by_id.get(doc.document_type_id)
        if doc_type is not None:
            approved_current.setdefault(doc.transport_id, set()).add(doc_type.key)

    result: dict[uuid.UUID, list[str]] = {}
    for transport in transports:
        required = required_type_keys(types, transport, orders.get(transport.order_id))
        missing = sorted(required - approved_current.get(transport.id, set()))
        result[transport.id] = missing
    return result
