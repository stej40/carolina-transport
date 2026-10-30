"""Append-only audit log of transport state changes and order-level events."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import utcnow

EVENT_TYPES = ("state_change", "assignment", "note", "document_submitted", "document_review")


class TransportEvent(Base):
    __tablename__ = "transport_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('state_change', 'assignment', 'note', "
            "'document_submitted', 'document_review')",
            name="ck_transport_events_event_type",
        ),
        CheckConstraint(
            "(transport_id IS NOT NULL) != (order_id IS NOT NULL)",
            name="ck_transport_events_single_subject",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transport_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("transports.id"), nullable=True, index=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("orders.id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
