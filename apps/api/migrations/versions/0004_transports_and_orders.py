"""transports & orders: orders, transports, transport_drivers, transport_events,
portal_settings, external_ids, idempotency_keys

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.String(length=64), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=True),
        sa.Column("counterparty_name", sa.String(length=255), nullable=False),
        sa.Column("counterparty_ico", sa.String(length=16), nullable=True),
        sa.Column("direction", sa.String(length=3), nullable=False, server_default="in"),
        sa.Column("cargo_text", sa.Text(), nullable=False),
        sa.Column("cargo_code", sa.String(length=64), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="CZK"),
        sa.Column("vat_rate", sa.Numeric(precision=4, scale=1), nullable=False),
        sa.Column("price_total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("loading_place", sa.Text(), nullable=False),
        sa.Column("loading_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("loading_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unloading_place", sa.Text(), nullable=False),
        sa.Column("unloading_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unloading_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("vehicle_requirements", sa.Text(), nullable=True),
        sa.Column("goods_status", sa.Text(), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "number", name="uq_orders_group_number"),
        sa.CheckConstraint("direction IN ('in', 'out')", name="ck_orders_direction"),
        sa.CheckConstraint("currency IN ('CZK', 'EUR')", name="ck_orders_currency"),
    )
    op.create_index(op.f("ix_orders_group_id"), "orders", ["group_id"], unique=False)

    op.create_table(
        "transports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("truck_id", sa.Uuid(), nullable=True),
        sa.Column("trailer_id", sa.Uuid(), nullable=True),
        sa.Column("is_international", sa.Boolean(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("planned_loading_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_unloading_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["truck_id"], ["trucks.id"]),
        sa.ForeignKeyConstraint(["trailer_id"], ["trailers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transports_group_id"), "transports", ["group_id"], unique=False)
    op.create_index(op.f("ix_transports_order_id"), "transports", ["order_id"], unique=False)

    op.create_table(
        "transport_drivers",
        sa.Column("transport_id", sa.Uuid(), nullable=False),
        sa.Column("driver_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by", sa.Uuid(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["transport_id"], ["transports.id"]),
        sa.ForeignKeyConstraint(["driver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("transport_id", "driver_id"),
    )
    op.create_index(
        op.f("ix_transport_drivers_driver_id"), "transport_drivers", ["driver_id"], unique=False
    )

    op.create_table(
        "transport_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transport_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("from_state", sa.String(length=32), nullable=True),
        sa.Column("to_state", sa.String(length=32), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["transport_id"], ["transports.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "event_type IN ('state_change', 'assignment', 'note')",
            name="ck_transport_events_event_type",
        ),
        sa.CheckConstraint(
            "(transport_id IS NOT NULL) != (order_id IS NOT NULL)",
            name="ck_transport_events_single_subject",
        ),
    )
    op.create_index(
        op.f("ix_transport_events_transport_id"), "transport_events", ["transport_id"], unique=False
    )
    op.create_index(
        op.f("ix_transport_events_order_id"), "transport_events", ["order_id"], unique=False
    )

    op.create_table(
        "portal_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("default_currency", sa.String(length=3), nullable=False, server_default="CZK"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "default_currency IN ('CZK', 'EUR')", name="ck_portal_settings_default_currency"
        ),
    )
    op.execute(
        "INSERT INTO portal_settings (id, default_currency, updated_at) "
        "VALUES ('00000000-0000-0000-0000-000000000001', 'CZK', '1970-01-01 00:00:00')"
    )

    op.create_table(
        "external_ids",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("system", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("system", "entity_type", "external_id", name="uq_external_ids_lookup"),
    )
    op.create_index(op.f("ix_external_ids_entity_id"), "external_ids", ["entity_id"], unique=False)

    op.create_table(
        "idempotency_keys",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "key"),
    )


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_index(op.f("ix_external_ids_entity_id"), table_name="external_ids")
    op.drop_table("external_ids")
    op.drop_table("portal_settings")
    op.drop_index(op.f("ix_transport_events_order_id"), table_name="transport_events")
    op.drop_index(op.f("ix_transport_events_transport_id"), table_name="transport_events")
    op.drop_table("transport_events")
    op.drop_index(op.f("ix_transport_drivers_driver_id"), table_name="transport_drivers")
    op.drop_table("transport_drivers")
    op.drop_index(op.f("ix_transports_order_id"), table_name="transports")
    op.drop_index(op.f("ix_transports_group_id"), table_name="transports")
    op.drop_table("transports")
    op.drop_index(op.f("ix_orders_group_id"), table_name="orders")
    op.drop_table("orders")
