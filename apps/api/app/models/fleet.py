"""Fleet master data: trucks and trailers."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import utcnow


class FleetMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    spz: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    group_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("groups.id"), index=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Truck(FleetMixin, Base):
    __tablename__ = "trucks"


class Trailer(FleetMixin, Base):
    __tablename__ = "trailers"
