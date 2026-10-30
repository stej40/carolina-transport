"""Document schemas: presigned upload ticket, versioned document, review."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DocumentStatus = Literal["draft", "pending_review", "accepted", "rejected"]
ReviewDecision = Literal["approve", "reject"]


class DocumentCreate(BaseModel):
    id: uuid.UUID | None = None
    document_type_id: uuid.UUID
    source: Literal["photo", "digital_file", "e_cmr"] = "photo"
    mime: str | None = Field(default=None, max_length=128)
    captured_at: datetime | None = None
    resubmits_document_id: uuid.UUID | None = None


class DocumentReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    reviewer_id: uuid.UUID
    decision: str
    reason: str | None
    created_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    group_id: uuid.UUID
    transport_id: uuid.UUID
    document_type_id: uuid.UUID
    variant: str
    source: str
    mime: str | None
    status: str
    version: int
    supersedes_id: uuid.UUID | None
    attributes: dict[str, Any]
    captured_at: datetime | None
    created_by: uuid.UUID
    created_at: datetime
    confirmed_at: datetime | None
    reviews: list[DocumentReviewOut] = []


class DocumentUploadTicket(BaseModel):
    document: DocumentOut
    upload_url: str
    expires_in_sec: int


class DocumentConfirmOut(BaseModel):
    document: DocumentOut


class DocumentReviewCreate(BaseModel):
    decision: ReviewDecision
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def reject_requires_reason(self) -> "DocumentReviewCreate":
        if self.decision == "reject" and not (self.reason or "").strip():
            raise ValueError("reason is required when rejecting a document")
        return self


class DocumentAttributesUpdate(BaseModel):
    attributes: dict[str, Any]
