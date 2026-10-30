"""Append-only event log writer (constraint 5). Rows are INSERT-only."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TransportEvent


def append_event(
    session: AsyncSession,
    *,
    event_type: str,
    transport_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
    from_state: str | None = None,
    to_state: str | None = None,
    actor_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> TransportEvent:
    event = TransportEvent(
        transport_id=transport_id,
        order_id=order_id,
        event_type=event_type,
        from_state=from_state,
        to_state=to_state,
        actor_id=actor_id,
        payload=payload or {},
    )
    session.add(event)
    return event
