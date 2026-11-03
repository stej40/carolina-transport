"""Fleet master data: trucks and trailers."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import utcnow

SPZ_ACTIVE_WHERE = text("retired_at IS NULL")


class FleetMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    spz: Mapped[str] = mapped_column(String(32))
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("groups.id"), index=True, nullable=True
    )
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Truck(FleetMixin, Base):
    __tablename__ = "trucks"
    __table_args__ = (
        Index(
            "uq_trucks_spz_active",
            "spz",
            unique=True,
            postgresql_where=SPZ_ACTIVE_WHERE,
            sqlite_where=SPZ_ACTIVE_WHERE,
        ),
    )


class Trailer(FleetMixin, Base):
    __tablename__ = "trailers"
    __table_args__ = (
        Index(
            "uq_trailers_spz_active",
            "spz",
            unique=True,
            postgresql_where=SPZ_ACTIVE_WHERE,
            sqlite_where=SPZ_ACTIVE_WHERE,
        ),
    )
