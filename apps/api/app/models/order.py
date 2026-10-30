"""Transport orders: billing-ready dispatcher-entered work requests."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import utcnow


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("group_id", "number", name="uq_orders_group_number"),
        CheckConstraint("direction IN ('in', 'out')", name="ck_orders_direction"),
        CheckConstraint("currency IN ('CZK', 'EUR')", name="ck_orders_currency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("groups.id"), nullable=False, index=True
    )
    number: Mapped[str] = mapped_column(String(64), nullable=False)
    order_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    counterparty_name: Mapped[str] = mapped_column(String(255), nullable=False)
    counterparty_ico: Mapped[str | None] = mapped_column(String(16), nullable=True)
    direction: Mapped[str] = mapped_column(
        String(3), nullable=False, default="in", server_default="in"
    )
    cargo_text: Mapped[str] = mapped_column(Text, nullable=False)
    cargo_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="CZK", server_default="CZK"
    )
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    price_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    loading_place: Mapped[str] = mapped_column(Text, nullable=False)
    loading_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    loading_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unloading_place: Mapped[str] = mapped_column(Text, nullable=False)
    unloading_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unloading_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    vehicle_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    goods_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
