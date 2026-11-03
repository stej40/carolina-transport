"""fleet retirement and group unassignment: retired_at, nullable group_id, partial SPZ uniqueness

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("trucks", "trailers"):
        op.add_column(
            table,
            sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.alter_column(table, "group_id", existing_type=sa.Uuid(), nullable=True)
        op.drop_index(op.f(f"ix_{table}_spz"), table_name=table)
        op.create_index(
            f"uq_{table}_spz_active",
            table,
            ["spz"],
            unique=True,
            postgresql_where=sa.text("retired_at IS NULL"),
            sqlite_where=sa.text("retired_at IS NULL"),
        )


def downgrade() -> None:
    for table in ("trailers", "trucks"):
        op.drop_index(f"uq_{table}_spz_active", table_name=table)
        op.create_index(op.f(f"ix_{table}_spz"), table_name=table, columns=["spz"], unique=True)
        op.alter_column(table, "group_id", existing_type=sa.Uuid(), nullable=False)
        op.drop_column(table, "retired_at")
