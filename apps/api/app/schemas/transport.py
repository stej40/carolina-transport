"""Transport schemas. The `id` is client-generatable for offline creation."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TransitionEvent = Literal[
    "arrive_loading",
    "start_transit",
    "arrive_unloading",
    "finish_unloading",
    "hand_in_documents",
    "resubmit",
    "accept",
    "reject",
    "cancel",
]


class TransportCreate(BaseModel):
    id: uuid.UUID | None = None
    order_id: uuid.UUID
    truck_id: uuid.UUID | None = None
    trailer_id: uuid.UUID | None = None
    is_international: bool = False
    planned_loading_at: datetime | None = None
    planned_unloading_at: datetime | None = None


class TransportDriversAssign(BaseModel):
    driver_ids: list[uuid.UUID] = Field(min_length=1, max_length=2)


class TransportTransition(BaseModel):
    event: TransitionEvent


class TransportOut(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    order_id: uuid.UUID
    state: str
    driver_ids: list[uuid.UUID]
    truck_id: uuid.UUID | None
    trailer_id: uuid.UUID | None
    is_international: bool
    planned_loading_at: datetime | None
    planned_unloading_at: datetime | None
    completed_at: datetime | None
    documents_complete: bool
    missing_documents: list[str]
