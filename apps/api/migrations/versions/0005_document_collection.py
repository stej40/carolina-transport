"""document collection: document_types, documents (+version), document_reviews;
extend transport_events event types with document audit events; seed the
taxonomy from the signed discovery design (mvp1-domain-discovery design.md §1)

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-30
"""

import json

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels = None
depends_on = None

_SEED = [
    (
        "00000000-0000-0000-0000-000000000010",
        "transport_order",
        "Přepravní smlouva (objednávka o přepravě)",
        "Transportvertrag (Transportbestellung)",
        "none",
        True,
        True,
        {
            "fields": [
                {"name": "number", "label": "Číslo", "required": True},
                {"name": "date", "label": "Datum", "required": True},
                {"name": "counterparty_name", "label": "Objednatel", "required": True},
                {"name": "cargo_text", "label": "Zboží", "required": False},
            ]
        },
    ),
    (
        "00000000-0000-0000-0000-000000000011",
        "cmr",
        "Mezinárodní nakladní list (CMR)",
        "Internationaler Frachtbrief (CMR)",
        "none",
        False,
        True,
        {
            "fields": [
                {"name": "cmr_number", "label": "Číslo CMR", "required": True},
                {"name": "gross_weight", "label": "Hrubá hmotnost (box 7)", "required": False},
                {
                    "name": "consignee_signed_at",
                    "label": "Podpis + razítko příjemce",
                    "required": False,
                },
            ]
        },
    ),
    (
        "00000000-0000-0000-0000-000000000012",
        "weighbridge_ticket_loading",
        "Vážní lístek – nakládka",
        "Wiegeschein – Beladung",
        "loading",
        False,
        True,
        {
            "fields": [
                {"name": "ticket_number", "label": "Číslo lístku", "required": True},
                {"name": "net_weight", "label": "Čistá hmotnost [t] (Ntto)", "required": True},
                {"name": "weighed_at", "label": "Čas vážení", "required": False},
                {"name": "spz", "label": "SPZ", "required": False},
                {"name": "driver", "label": "Řidič", "required": False},
            ]
        },
    ),
    (
        "00000000-0000-0000-0000-000000000013",
        "weighbridge_ticket_unloading",
        "Vážní lístek – vykládka",
        "Wiegeschein – Entladung",
        "unloading",
        False,
        True,
        {
            "fields": [
                {"name": "ticket_number", "label": "Číslo lístku", "required": True},
                {"name": "net_weight", "label": "Čistá hmotnost [t] (Ntto)", "required": True},
                {"name": "weighed_at", "label": "Čas vážení", "required": False},
                {"name": "spz", "label": "SPZ", "required": False},
                {"name": "driver", "label": "Řidič", "required": False},
            ]
        },
    ),
    (
        "00000000-0000-0000-0000-000000000014",
        "cleaning_declaration",
        "ERKLÄRUNG – vyčištění korby",
        "ERKLÄRUNG – Reinigung der Mulde",
        "none",
        False,
        True,
        {
            "fields": [
                {"name": "cleaning_method", "label": "Způsob vyčištění", "required": True},
                {"name": "declared_at", "label": "Místo a datum", "required": True},
                {"name": "last_products", "label": "Předchozí 3 jízdy – zboží", "required": False},
            ]
        },
    ),
    (
        "00000000-0000-0000-0000-000000000015",
        "delivery_note",
        "Dodací list",
        "Lieferschein",
        "none",
        False,
        True,
        {
            "fields": [
                {"name": "number", "label": "Číslo", "required": True},
                {"name": "quantity", "label": "Množství", "required": False},
                {
                    "name": "consignee_signed_at",
                    "label": "Razítko + podpis příjemce",
                    "required": False,
                },
            ]
        },
    ),
    (
        "00000000-0000-0000-0000-000000000016",
        "customs_document",
        "Celní doklad DZV",
        "Zoll Dokument DZV",
        "none",
        False,
        False,
        {
            "fields": [
                {
                    "name": "dzv_reference",
                    "label": "Odkaz na potvrzenou kopii DZV",
                    "required": True,
                },
            ]
        },
    ),
]


def _sql_str(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _json_literal(schema: dict) -> str:
    escaped = json.dumps(schema, ensure_ascii=False).replace("'", "''")
    return f"'{escaped}'"


def upgrade() -> None:
    op.create_table(
        "document_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("label_cs", sa.String(length=255), nullable=False),
        sa.Column("label_de", sa.String(length=255), nullable=False),
        sa.Column("attribute_schema", sa.JSON(), nullable=False),
        sa.Column("variant", sa.String(length=16), nullable=False, server_default="none"),
        sa.Column("default_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_document_types_key"),
        sa.CheckConstraint(
            "variant IN ('none', 'loading', 'unloading')", name="ck_document_types_variant"
        ),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("transport_id", sa.Uuid(), nullable=False),
        sa.Column("document_type_id", sa.Uuid(), nullable=False),
        sa.Column("variant", sa.String(length=16), nullable=False, server_default="none"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="photo"),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("mime", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("supersedes_id", sa.Uuid(), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["transport_id"], ["transports.id"]),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"]),
        sa.ForeignKeyConstraint(["supersedes_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('draft', 'pending_review', 'accepted', 'rejected')",
            name="ck_documents_status",
        ),
        sa.CheckConstraint(
            "source IN ('photo', 'digital_file', 'e_cmr', 'generated')",
            name="ck_documents_source",
        ),
        sa.CheckConstraint("version >= 1", name="ck_documents_version"),
    )
    op.create_index(op.f("ix_documents_group_id"), "documents", ["group_id"], unique=False)
    op.create_index(op.f("ix_documents_transport_id"), "documents", ["transport_id"], unique=False)
    op.create_index(
        op.f("ix_documents_document_type_id"), "documents", ["document_type_id"], unique=False
    )

    op.create_table(
        "document_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "decision IN ('approve', 'reject')", name="ck_document_reviews_decision"
        ),
    )
    op.create_index(
        op.f("ix_document_reviews_document_id"), "document_reviews", ["document_id"], unique=False
    )

    # Document audit events on the transport event log (discovery design §3).
    op.drop_constraint("ck_transport_events_event_type", "transport_events", type_="check")
    op.create_check_constraint(
        "ck_transport_events_event_type",
        "transport_events",
        "event_type IN ('state_change', 'assignment', 'note', "
        "'document_submitted', 'document_review')",
    )

    rows = ", ".join(
        "({}, {}, {}, {}, {}, {}, {}, {}, '1970-01-01 00:00:00')".format(
            _sql_str(doc_id),
            _sql_str(key),
            _sql_str(label_cs),
            _sql_str(label_de),
            _sql_str(variant),
            "true" if default_required else "false",
            "true" if is_active else "false",
            _json_literal(schema),
        )
        for doc_id, key, label_cs, label_de, variant, default_required, is_active, schema in _SEED
    )
    op.execute(
        "INSERT INTO document_types "
        "(id, key, label_cs, label_de, variant, default_required, is_active, "
        "attribute_schema, created_at) VALUES " + rows
    )


def downgrade() -> None:
    op.drop_constraint("ck_transport_events_event_type", "transport_events", type_="check")
    op.create_check_constraint(
        "ck_transport_events_event_type",
        "transport_events",
        "event_type IN ('state_change', 'assignment', 'note')",
    )
    op.drop_index(op.f("ix_document_reviews_document_id"), table_name="document_reviews")
    op.drop_table("document_reviews")
    op.drop_index(op.f("ix_documents_document_type_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_transport_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_group_id"), table_name="documents")
    op.drop_table("documents")
    op.drop_table("document_types")
