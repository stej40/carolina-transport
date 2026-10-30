"""Documents: one row per version; resubmission supersedes, never overwrites."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import utcnow

DOC_STATUS_DRAFT = "draft"
DOC_STATUS_PENDING_REVIEW = "pending_review"
DOC_STATUS_ACCEPTED = "accepted"
DOC_STATUS_REJECTED = "rejected"
DOCUMENT_STATUSES = (
    DOC_STATUS_DRAFT,
    DOC_STATUS_PENDING_REVIEW,
    DOC_STATUS_ACCEPTED,
    DOC_STATUS_REJECTED,
)
DOC_SOURCES = ("photo", "digital_file", "e_cmr", "generated")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            f"status IN ('{DOC_STATUS_DRAFT}', '{DOC_STATUS_PENDING_REVIEW}', "
            f"'{DOC_STATUS_ACCEPTED}', '{DOC_STATUS_REJECTED}')",
            name="ck_documents_status",
        ),
        CheckConstraint(
            "source IN ('photo', 'digital_file', 'e_cmr', 'generated')",
            name="ck_documents_source",
        ),
        CheckConstraint("version >= 1", name="ck_documents_version"),
    )

    # PK is client-generatable for offline creation (constraint 3).
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("groups.id"), nullable=False, index=True
    )
    transport_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transports.id"), nullable=False, index=True
    )
    document_type_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("document_types.id"), nullable=False, index=True
    )
    variant: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="photo")
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=DOC_STATUS_DRAFT)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("documents.id"), nullable=True
    )
    # OCR-ready extracted/manual attributes (MVP3 fills this further).
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
