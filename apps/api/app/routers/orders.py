"""Order CRUD, editing audit and the cancel cascade."""

import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import ScopedGroupIds, Session, group_in_scope, require_roles
from app.event_log import append_event
from app.models import ADMIN_ROLES, Order, PortalSettings, Transport, User
from app.schemas import OrderCreate, OrderOut, OrderUpdate
from app.transport_state import EVENT_ORDER_CANCELLED, NOT_YET_COMPLETED_STATES, can_transition

router = APIRouter(prefix="/orders", tags=["orders"])

OrderCaller = Annotated[User, Depends(require_roles("dispatcher", *ADMIN_ROLES))]


async def _get_order_or_404(
    session: Session, order_id: uuid.UUID, scoped: set[uuid.UUID] | None
) -> Order:
    order = await session.get(Order, order_id)
    if order is None or not group_in_scope(scoped, order.group_id):
        raise HTTPException(status_code=404, detail="Order not found")
    return order


async def _default_currency(session: Session) -> str:
    settings_row: PortalSettings | None = (
        await session.execute(select(PortalSettings).limit(1))
    ).scalar_one_or_none()
    if settings_row is None:
        settings_row = PortalSettings()
        session.add(settings_row)
        await session.commit()
    return settings_row.default_currency


def _line_total(quantity: Decimal, unit_price: Decimal) -> Decimal:
    return (quantity * unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _is_editable(order: Order) -> bool:
    # MVP1: no invoice entity exists, so orders stay editable. MVP2 will
    # reject billing-field writes once an invoice is linked (design.md).
    return True


@router.post("", response_model=OrderOut, status_code=201)
async def create_order(
    body: OrderCreate, session: Session, scoped: ScopedGroupIds, caller: OrderCaller
) -> Order:
    if not group_in_scope(scoped, body.group_id):
        raise HTTPException(status_code=404, detail="Group not found")
    currency = body.currency or await _default_currency(session)
    order = Order(
        **body.model_dump(exclude={"currency", "price_total"}),
        currency=currency,
        price_total=_line_total(body.quantity, body.unit_price),
    )
    session.add(order)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="Order number already used in this group"
        ) from None
    await session.refresh(order)
    return order


@router.get("", response_model=list[OrderOut])
async def list_orders(session: Session, scoped: ScopedGroupIds, caller: OrderCaller) -> list[Order]:
    stmt = select(Order).order_by(Order.created_at.desc(), Order.number)
    if scoped is not None:
        if not scoped:
            return []
        stmt = stmt.where(Order.group_id.in_(scoped))
    return list((await session.execute(stmt)).scalars().all())


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: uuid.UUID, session: Session, scoped: ScopedGroupIds, caller: OrderCaller
) -> Order:
    return await _get_order_or_404(session, order_id, scoped)


@router.patch("/{order_id}", response_model=OrderOut)
async def update_order(
    order_id: uuid.UUID,
    body: OrderUpdate,
    session: Session,
    scoped: ScopedGroupIds,
    caller: OrderCaller,
) -> Order:
    order = await _get_order_or_404(session, order_id, scoped)
    if not _is_editable(order):
        raise HTTPException(
            status_code=409, detail="Order is linked to an invoice and no longer editable"
        )
    changes = body.model_dump(exclude_unset=True)
    changed_fields: list[str] = []
    for field, value in changes.items():
        if getattr(order, field) != value:
            setattr(order, field, value)
            changed_fields.append(field)
    if {"quantity", "unit_price"} & set(changed_fields):
        order.price_total = _line_total(order.quantity, order.unit_price)
    if changed_fields:
        append_event(
            session,
            event_type="note",
            order_id=order.id,
            actor_id=caller.id,
            payload={"action": "order_updated", "changed": changed_fields},
        )
    await session.commit()
    await session.refresh(order)
    return order


@router.post("/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(
    order_id: uuid.UUID, session: Session, scoped: ScopedGroupIds, caller: OrderCaller
) -> Order:
    order = await _get_order_or_404(session, order_id, scoped)
    if order.cancelled_at is not None:
        raise HTTPException(status_code=409, detail="Order already cancelled")
    order.cancelled_at = datetime.now(UTC)
    transports = (
        (await session.execute(select(Transport).where(Transport.order_id == order.id)))
        .scalars()
        .all()
    )
    cancelled_ids: list[str] = []
    for transport in transports:
        if transport.state not in NOT_YET_COMPLETED_STATES:
            continue
        target = can_transition(transport.state, EVENT_ORDER_CANCELLED)
        if target is None:
            continue
        from_state = transport.state
        transport.state = target
        append_event(
            session,
            event_type="state_change",
            transport_id=transport.id,
            from_state=from_state,
            to_state=target,
            actor_id=caller.id,
            payload={"reason": "order_cancelled"},
        )
        cancelled_ids.append(str(transport.id))
    append_event(
        session,
        event_type="note",
        order_id=order.id,
        actor_id=caller.id,
        payload={"action": "order_cancelled", "cancelled_transport_ids": cancelled_ids},
    )
    await session.commit()
    await session.refresh(order)
    return order
