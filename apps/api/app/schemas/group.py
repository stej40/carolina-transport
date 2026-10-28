"""Group schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.fleet import FleetOut
from app.schemas.user import UserOut


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class GroupUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class GroupMove(BaseModel):
    group_id: uuid.UUID


class GroupDetailOut(GroupOut):
    members: list[UserOut] = []
    drivers: list[UserOut] = []
    trucks: list[FleetOut] = []
    trailers: list[FleetOut] = []
