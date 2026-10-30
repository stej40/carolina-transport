"""Order request/response schemas. Billing-ready fields are required;
`direction` accepts 'in' only in MVP1 ('out' is the reserved subcontracting
follow-up from the signed discovery schema)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Currency = Literal["CZK", "EUR"]
Direction = Literal["in"]


class OrderCreate(BaseModel):
    group_id: uuid.UUID
    number: str = Field(min_length=1, max_length=64)
    order_date: date | None = None
    counterparty_name: str = Field(min_length=1, max_length=255)
    counterparty_ico: str | None = Field(default=None, max_length=16)
    direction: Direction = "in"
    cargo_text: str = Field(min_length=1)
    cargo_code: str | None = Field(default=None, max_length=64)
    quantity: Decimal = Field(gt=0)
    unit: str = Field(min_length=1, max_length=16)
    unit_price: Decimal = Field(ge=0)
    currency: Currency | None = None
    vat_rate: Decimal = Field(ge=0, le=Decimal("99.9"))
    loading_place: str = Field(min_length=1)
    loading_from: datetime | None = None
    loading_to: datetime | None = None
    unloading_place: str = Field(min_length=1)
    unloading_from: datetime | None = None
    unloading_to: datetime | None = None
    vehicle_requirements: str | None = None
    goods_status: str | None = None
    instructions: str | None = None
    terms: str | None = None


class OrderUpdate(BaseModel):
    number: str | None = Field(default=None, min_length=1, max_length=64)
    order_date: date | None = None
    counterparty_name: str | None = Field(default=None, min_length=1, max_length=255)
    counterparty_ico: str | None = Field(default=None, max_length=16)
    cargo_text: str | None = Field(default=None, min_length=1)
    cargo_code: str | None = Field(default=None, max_length=64)
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, min_length=1, max_length=16)
    unit_price: Decimal | None = Field(default=None, ge=0)
    currency: Currency | None = None
    vat_rate: Decimal | None = Field(default=None, ge=0, le=Decimal("99.9"))
    loading_place: str | None = Field(default=None, min_length=1)
    loading_from: datetime | None = None
    loading_to: datetime | None = None
    unloading_place: str | None = Field(default=None, min_length=1)
    unloading_from: datetime | None = None
    unloading_to: datetime | None = None
    vehicle_requirements: str | None = None
    goods_status: str | None = None
    instructions: str | None = None
    terms: str | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    group_id: uuid.UUID
    number: str
    order_date: date | None
    counterparty_name: str
    counterparty_ico: str | None
    direction: str
    cargo_text: str
    cargo_code: str | None
    quantity: Decimal
    unit: str
    unit_price: Decimal
    currency: str
    vat_rate: Decimal
    price_total: Decimal
    loading_place: str
    loading_from: datetime | None
    loading_to: datetime | None
    unloading_place: str
    unloading_from: datetime | None
    unloading_to: datetime | None
    vehicle_requirements: str | None
    goods_status: str | None
    instructions: str | None
    terms: str | None
    cancelled_at: datetime | None
