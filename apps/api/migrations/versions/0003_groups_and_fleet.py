"""organizational groups: groups, group_members, trucks, trailers, users.group_id

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "group_members",
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("group_id", "user_id"),
    )
    op.create_index(op.f("ix_group_members_user_id"), "group_members", ["user_id"], unique=False)

    for table in ("trucks", "trailers"):
        op.create_table(
            table,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("spz", sa.String(length=32), nullable=False),
            sa.Column("group_id", sa.Uuid(), nullable=False),
            sa.Column("label", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f(f"ix_{table}_spz"), table, ["spz"], unique=True)
        op.create_index(op.f(f"ix_{table}_group_id"), table, ["group_id"], unique=False)

    op.add_column("users", sa.Column("group_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_users_group_id"), "users", ["group_id"], unique=False)
    op.create_foreign_key("fk_users_group_id", "users", "groups", ["group_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_users_group_id", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_group_id"), table_name="users")
    op.drop_column("users", "group_id")
    for table in ("trailers", "trucks"):
        op.drop_index(op.f(f"ix_{table}_group_id"), table_name=table)
        op.drop_index(op.f(f"ix_{table}_spz"), table_name=table)
        op.drop_table(table)
    op.drop_index(op.f("ix_group_members_user_id"), table_name="group_members")
    op.drop_table("group_members")
    op.drop_table("groups")
