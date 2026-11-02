"""User schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import Language, Role


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


class UserRolesReplace(BaseModel):
    # Empty list is valid: it strips all roles (see design decision 3).
    roles: list[Role]
    group_id: uuid.UUID | None = None

    @field_validator("roles")
    @classmethod
    def _unique_roles(cls, value: list[Role]) -> list[Role]:
        if len(set(value)) != len(value):
            raise ValueError("roles must be unique")
        return value


class ProfileUpdate(BaseModel):
    language: Language
