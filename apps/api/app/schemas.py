import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Language = Literal["cs", "en", "de"]
Role = Literal["driver", "dispatcher", "company-admin", "system-admin"]


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    roles: list[str]
    language: Language
    is_active: bool
    group_id: uuid.UUID | None = None


class UserCreate(BaseModel):
    email: str = Field(min_length=3)
    name: str = Field(min_length=1)
    password: str = Field(min_length=8)
    roles: list[Role] = Field(min_length=1)


class ProfileUpdate(BaseModel):
    language: Language


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class GroupUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class FleetCreate(BaseModel):
    spz: str = Field(min_length=1, max_length=32)
    group_id: uuid.UUID
    label: str | None = Field(default=None, max_length=255)


class FleetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    spz: str
    group_id: uuid.UUID
    label: str | None


class GroupMove(BaseModel):
    group_id: uuid.UUID


class GroupDetailOut(GroupOut):
    members: list[UserOut] = []
    drivers: list[UserOut] = []
    trucks: list[FleetOut] = []
    trailers: list[FleetOut] = []
