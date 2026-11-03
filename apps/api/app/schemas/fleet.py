"""Fleet master-data schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FleetCreate(BaseModel):
    spz: str = Field(min_length=1, max_length=32)
    group_id: uuid.UUID
    label: str | None = Field(default=None, max_length=255)


class FleetUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=255)


class FleetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    spz: str
    group_id: uuid.UUID | None
    label: str | None
    retired_at: datetime | None
