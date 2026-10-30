"""Company-wide portal configuration singleton row."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import utcnow


class PortalSettings(Base):
    __tablename__ = "portal_settings"
    __table_args__ = (
        CheckConstraint(
            "default_currency IN ('CZK', 'EUR')", name="ck_portal_settings_default_currency"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    default_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="CZK", server_default="CZK"
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
