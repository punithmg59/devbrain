"""Explainable risk engine tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "risk_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("risk_category", sa.Text(), server_default="safe", nullable=False),
        sa.Column("risk_factors", postgresql.JSONB(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["repo_id"], ["repos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repo_id", "entity_type", "entity_id", name="uq_risk_profiles_repo_entity"),
    )
    op.create_index("ix_risk_profiles_repo_id", "risk_profiles", ["repo_id"])
    op.create_index("ix_risk_profiles_entity", "risk_profiles", ["repo_id", "entity_type", "entity_id"])

    op.create_table(
        "risk_breakdowns",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("factor_name", sa.Text(), nullable=False),
        sa.Column("factor_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("weight", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["repo_id"], ["repos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_breakdowns_repo_id", "risk_breakdowns", ["repo_id"])

    op.create_table(
        "risk_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("new_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["repo_id"], ["repos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_history_repo_id", "risk_history", ["repo_id"])


def downgrade() -> None:
    op.drop_index("ix_risk_history_repo_id", table_name="risk_history")
    op.drop_table("risk_history")
    op.drop_index("ix_risk_breakdowns_repo_id", table_name="risk_breakdowns")
    op.drop_table("risk_breakdowns")
    op.drop_index("ix_risk_profiles_entity", table_name="risk_profiles")
    op.drop_index("ix_risk_profiles_repo_id", table_name="risk_profiles")
    op.drop_table("risk_profiles")
