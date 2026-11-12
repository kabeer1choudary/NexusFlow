"""initial schema

Revision ID: 0001_init
Revises:
Create Date: 2026-11-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

from nxflow.db_sql import TRIGGER_STATEMENTS

revision: str = "0001_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="declared"),
        sa.Column("location", sa.String(512), nullable=True),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default=sa.text("'{}'::varchar[]"),
        ),
        sa.Column(
            "attributes",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "origin",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("type", "name", name="uq_resources_type_name"),
    )
    op.create_index("ix_res_type_status", "resources", ["type", "status"])
    op.create_index(
        "ix_res_tags", "resources", ["tags"], postgresql_using="gin"
    )
    op.create_index(
        "ix_res_attributes",
        "resources",
        ["attributes"],
        postgresql_using="gin",
        postgresql_ops={"attributes": "jsonb_path_ops"},
    )
    op.create_index(
        "ix_res_metadata",
        "resources",
        ["metadata"],
        postgresql_using="gin",
        postgresql_ops={"metadata": "jsonb_path_ops"},
    )
    op.create_index(
        "ix_res_location", "resources", ["location"], postgresql_ops={"location": "text_pattern_ops"}
    )

    op.create_table(
        "relationships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rel_type", sa.String(64), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("source_id", "target_id", "rel_type", name="uq_relationships_edge"),
    )
    op.create_index("ix_rel_source", "relationships", ["source_id", "rel_type"])
    op.create_index("ix_rel_target", "relationships", ["target_id", "rel_type"])

    op.create_table(
        "resource_history",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False, server_default="system"),
        sa.Column("source", sa.Text(), nullable=False, server_default="api"),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column("delta", postgresql.JSONB(), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_hist_resource", "resource_history", ["resource_id", "recorded_at"]
    )

    if context.is_offline_mode():
        for statement in TRIGGER_STATEMENTS:
            op.execute(statement)
    else:
        bind = op.get_bind()
        for statement in TRIGGER_STATEMENTS:
            bind.exec_driver_sql(statement)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_history_immutable ON resource_history")
    op.execute("DROP TRIGGER IF EXISTS trg_resources_audit ON resources")
    op.execute("DROP FUNCTION IF EXISTS nxflow_history_immutable()")
    op.execute("DROP FUNCTION IF EXISTS nxflow_resource_audit()")
    op.drop_table("resource_history")
    op.drop_table("relationships")
    op.drop_table("resources")
