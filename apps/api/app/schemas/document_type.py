"""Document-type taxonomy schemas (taxonomy is data, constraint 7)."""

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Variant = Literal["none", "loading", "unloading"]
Source = Literal["photo", "digital_file", "e_cmr", "generated"]


class DocumentTypeCreate(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    label_cs: str = Field(min_length=1, max_length=255)
    label_de: str = Field(min_length=1, max_length=255)
    attribute_schema: dict[str, Any] = Field(default_factory=dict)
    variant: Variant = "none"
    default_required: bool = False
    is_active: bool = True


class DocumentTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    label_cs: str
    label_de: str
    attribute_schema: dict[str, Any]
    variant: str
    default_required: bool
    is_active: bool
