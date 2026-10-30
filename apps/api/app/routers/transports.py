"""Transports: creation on orders, driver pair, state transitions, history."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import (
    ScopedGroupIds,
    Session,
    effective_scope,
    group_in_scope,
    is_admin,
    is_dispatcher,
    require_roles,
)
from app.document_rules import missing_documents_for
from app.event_log import append_event
from app.models import (
    ADMIN_ROLES,
    Order,
    Transport,
    TransportDriver,
    TransportEvent,
    User,
)
from app.schemas import (
    TransportCreate,
    TransportDriversAssign,
    TransportEventOut,
    TransportOut,
    TransportTransition,
)
from app.transport_state import (
    DISPATCHER_EVENTS,
    DRIVER_EVENTS,
    EVENT_ASSIGN,
    EVENT_UNASSIGN,
    STATE_ASSIGNED,
    STATE_CANCELLED,
    STATE_COMPLETED,
    STATE_DRAFT,
    can_transition,
)

router = APIRouter(prefix="/transports", tags=["transports"])

DispatcherCaller = Annotated[User, Depends(require_roles("dispatcher", *ADMIN_ROLES))]
AnyCaller = Annotated[User, Depends(require_roles("driver", "dispatcher", *ADMIN_ROLES))]


async def _driver_ids(session: Session, transport_id: uuid.UUID) -> list[uuid.UUID]:
    rows = await session.execute(
        select(TransportDriver.driver_id).where(TransportDriver.transport_id == transport_id)
    )
    return list(rows.scalars().all())


async def _to_out(
    session: Session,
    transport: Transport,
    missing_map: dict[uuid.UUID, list[str]] | None = None,
) -> TransportOut:
    if missing_map is None:
        missing_map = await missing_documents_for(session, [transport])
    missing = missing_map.get(transport.id, [])
    return TransportOut(
        id=transport.id,
        group_id=transport.group_id,
        order_id=transport.order_id,
        state=transport.state,
        driver_ids=await _driver_ids(session, transport.id),
        truck_id=transport.truck_id,
        trailer_id=transport.trailer_id,
        is_international=transport.is_international,
        planned_loading_at=transport.planned_loading_at,
        planned_unloading_at=transport.planned_unloading_at,
        completed_at=transport.completed_at,
        documents_complete=not missing,
        missing_documents=missing,
    )


async def _get_transport_or_404(
    session: Session, transport_id: uuid.UUID, scoped: set[uuid.UUID] | None
) -> Transport:
    transport = await session.get(Transport, transport_id)
    if transport is None or not group_in_scope(scoped, transport.group_id):
        raise HTTPException(status_code=404, detail="Transport not found")
    return transport


@router.post("", response_model=TransportOut, status_code=201)
async def create_transport(
    body: TransportCreate, session: Session, scoped: ScopedGroupIds, caller: DispatcherCaller
) -> TransportOut:
    order = await session.get(Order, body.order_id)
    if order is None or not group_in_scope(scoped, order.group_id):
        raise HTTPException(status_code=404, detail="Order not found")
    if order.cancelled_at is not None:
        raise HTTPException(status_code=409, detail="Cancelled order cannot gain transports")
    transport_id = body.id or uuid.uuid4()
    if await session.get(Transport, transport_id) is not None:
        raise HTTPException(status_code=409, detail="Transport id already exists")
    transport = Transport(
        id=transport_id,
        group_id=order.group_id,
        order_id=order.id,
        truck_id=body.truck_id,
        trailer_id=body.trailer_id,
        is_international=body.is_international,
        planned_loading_at=body.planned_loading_at,
        planned_unloading_at=body.planned_unloading_at,
    )
    session.add(transport)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Unknown truck or trailer") from None
    return await _to_out(session, transport)


@router.get("", response_model=list[TransportOut])
async def list_transports(
    session: Session, scoped: ScopedGroupIds, caller: AnyCaller
) -> list[TransportOut]:
    scoped = effective_scope(caller, scoped)
    stmt = select(Transport).order_by(Transport.created_at.desc())
    if is_dispatcher(caller):
        if scoped is not None:
            if not scoped:
                return []
            stmt = stmt.where(Transport.group_id.in_(scoped))
    else:
        stmt = (
            stmt.join(TransportDriver, TransportDriver.transport_id == Transport.id)
            .where(TransportDriver.driver_id == caller.id)
            .where(Transport.state != STATE_CANCELLED)
        )
    transports = list((await session.execute(stmt)).scalars().all())
    missing_map = await missing_documents_for(session, transports)
    return [await _to_out(session, t, missing_map) for t in transports]


@router.get("/{transport_id}", response_model=TransportOut)
async def get_transport(
    transport_id: uuid.UUID, session: Session, scoped: ScopedGroupIds, caller: AnyCaller
) -> TransportOut:
    transport = await _get_transport_or_404(session, transport_id, effective_scope(caller, scoped))
    return await _to_out(session, transport)


@router.put("/{transport_id}/drivers", response_model=TransportOut)
async def assign_drivers(
    transport_id: uuid.UUID,
    body: TransportDriversAssign,
    session: Session,
    scoped: ScopedGroupIds,
    caller: DispatcherCaller,
) -> TransportOut:
    transport = await _get_transport_or_404(session, transport_id, scoped)
    if transport.state == STATE_CANCELLED:
        raise HTTPException(status_code=409, detail="Transport is cancelled")
    wanted = list(dict.fromkeys(body.driver_ids))
    current = set(await _driver_ids(session, transport.id))
    for driver_id in wanted:
        if driver_id in current:
            continue
        driver = await session.get(User, driver_id)
        if driver is None or not driver.is_active:
            raise HTTPException(status_code=404, detail="Driver not found")
        if "driver" not in driver.roles:
            raise HTTPException(status_code=400, detail="User is not a driver")
        if driver.group_id != transport.group_id:
            raise HTTPException(status_code=403, detail="Driver is not in the transport's group")
    to_add = [d for d in wanted if d not in current]
    to_remove = [d for d in current if d not in set(wanted)]
    for driver_id in to_remove:
        row = await session.get(TransportDriver, (transport.id, driver_id))
        if row is not None:
            await session.delete(row)
    for driver_id in to_add:
        session.add(
            TransportDriver(transport_id=transport.id, driver_id=driver_id, assigned_by=caller.id)
        )
    append_event(
        session,
        event_type="assignment",
        transport_id=transport.id,
        actor_id=caller.id,
        payload={"added": [str(d) for d in to_add], "removed": [str(d) for d in to_remove]},
    )
    if to_add and transport.state == STATE_DRAFT:
        target = can_transition(transport.state, EVENT_ASSIGN)
        assert target is not None
        append_event(
            session,
            event_type="state_change",
            transport_id=transport.id,
            from_state=transport.state,
            to_state=target,
            actor_id=caller.id,
            payload={"reason": "assign"},
        )
        transport.state = target
    await session.commit()
    return await _to_out(session, transport)


@router.delete("/{transport_id}/drivers/{driver_id}", response_model=TransportOut)
async def remove_driver(
    transport_id: uuid.UUID,
    driver_id: uuid.UUID,
    session: Session,
    scoped: ScopedGroupIds,
    caller: DispatcherCaller,
) -> TransportOut:
    transport = await _get_transport_or_404(session, transport_id, scoped)
    if transport.state == STATE_CANCELLED:
        raise HTTPException(status_code=409, detail="Transport is cancelled")
    row = await session.get(TransportDriver, (transport_id, driver_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Driver is not assigned to this transport")
    await session.delete(row)
    append_event(
        session,
        event_type="assignment",
        transport_id=transport.id,
        actor_id=caller.id,
        payload={"added": [], "removed": [str(driver_id)]},
    )
    remaining = [d for d in await _driver_ids(session, transport.id) if d != driver_id]
    if not remaining and transport.state == STATE_ASSIGNED:
        target = can_transition(transport.state, EVENT_UNASSIGN)
        assert target is not None
        append_event(
            session,
            event_type="state_change",
            transport_id=transport.id,
            from_state=transport.state,
            to_state=target,
            actor_id=caller.id,
            payload={"reason": "unassign"},
        )
        transport.state = target
    await session.commit()
    return await _to_out(session, transport)


@router.post("/{transport_id}/transitions", response_model=TransportOut)
async def transition_transport(
    transport_id: uuid.UUID,
    body: TransportTransition,
    session: Session,
    scoped: ScopedGroupIds,
    caller: AnyCaller,
) -> TransportOut:
    transport = await _get_transport_or_404(session, transport_id, effective_scope(caller, scoped))
    event = body.event
    if is_admin(caller):
        allowed = DRIVER_EVENTS | DISPATCHER_EVENTS
    elif is_dispatcher(caller):
        allowed = DISPATCHER_EVENTS
    else:
        assigned = set(await _driver_ids(session, transport.id))
        if caller.id not in assigned:
            raise HTTPException(status_code=403, detail="Driver is not assigned to this transport")
        allowed = DRIVER_EVENTS
    if event not in allowed:
        raise HTTPException(status_code=403, detail=f"Event {event} not permitted for your role")
    target = can_transition(transport.state, event)
    if target is None:
        raise HTTPException(
            status_code=409, detail=f"Transition {event} is not allowed from {transport.state}"
        )
    from_state = transport.state
    transport.state = target
    if target == STATE_COMPLETED:
        transport.completed_at = datetime.now(UTC)
    append_event(
        session,
        event_type="state_change",
        transport_id=transport.id,
        from_state=from_state,
        to_state=target,
        actor_id=caller.id,
        payload={"event": event},
    )
    await session.commit()
    return await _to_out(session, transport)


@router.get("/{transport_id}/history", response_model=list[TransportEventOut])
async def transport_history(
    transport_id: uuid.UUID, session: Session, scoped: ScopedGroupIds, caller: AnyCaller
) -> list[TransportEvent]:
    transport = await _get_transport_or_404(session, transport_id, effective_scope(caller, scoped))
    rows = await session.execute(
        select(TransportEvent)
        .where(TransportEvent.transport_id == transport.id)
        .order_by(TransportEvent.occurred_at, TransportEvent.id)
    )
    return list(rows.scalars().all())
