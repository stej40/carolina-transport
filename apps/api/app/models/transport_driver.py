"""Current driver pair per transport (max 2 enforced in the service layer)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import utcnow


class TransportDriver(Base):
    __tablename__ = "transport_drivers"

    transport_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transports.id"), primary_key=True
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), primary_key=True, index=True
    )
    assigned_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
