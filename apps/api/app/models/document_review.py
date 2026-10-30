"""Immutable review decisions per document version (audit, constraint 5)."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import utcnow

REVIEW_DECISIONS = ("approve", "reject")


class DocumentReview(Base):
    __tablename__ = "document_reviews"
    __table_args__ = (
        CheckConstraint("decision IN ('approve', 'reject')", name="ck_document_reviews_decision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.id"), nullable=False, index=True
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
