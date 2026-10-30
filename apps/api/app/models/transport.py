"""Transports: one execution run under an order (an order may have 1..N)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import utcnow
from app.transport_state import STATE_DRAFT


class Transport(Base):
    __tablename__ = "transports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("groups.id"), nullable=False, index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id"), nullable=False, index=True
    )
    truck_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("trucks.id"), nullable=True)
    trailer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("trailers.id"), nullable=True
    )
    is_international: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default=STATE_DRAFT)
    planned_loading_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    planned_unloading_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
