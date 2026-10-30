"""Document taxonomy as data (constraint 7): types + required attributes."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import utcnow

VARIANTS = ("none", "loading", "unloading")


class DocumentType(Base):
    __tablename__ = "document_types"
    __table_args__ = (
        UniqueConstraint("key", name="uq_document_types_key"),
        CheckConstraint(
            "variant IN ('none', 'loading', 'unloading')",
            name="ck_document_types_variant",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    label_cs: Mapped[str] = mapped_column(String(255), nullable=False)
    label_de: Mapped[str] = mapped_column(String(255), nullable=False)
    # schema-lite: {"fields": [{"name": ..., "label": ..., "required": bool}, ...]}
    attribute_schema: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    variant: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    default_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
