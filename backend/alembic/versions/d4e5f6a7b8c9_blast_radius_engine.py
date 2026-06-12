"""blast radius engine tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-31 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "blast_radius_cache",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["repo_id"], ["repos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_blast_radius_cache_lookup",
        "blast_radius_cache",
        ["repo_id", "target_node_id", "direction", "depth"],
    )
    op.create_index("ix_blast_radius_cache_expires", "blast_radius_cache", ["expires_at"])

    op.create_table(
        "critical_paths",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("criticality", sa.String(length=32), server_default="high", nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("path_nodes", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["repo_id"], ["repos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repo_id", "name", name="uq_critical_paths_repo_name"),
    )
    op.create_index("ix_critical_paths_repo_id", "critical_paths", ["repo_id"])

    op.create_table(
        "impact_metrics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dependency_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("workflow_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("service_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("api_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("journey_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("centrality_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("blast_radius_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("in_degree", sa.Integer(), server_default="0", nullable=False),
        sa.Column("out_degree", sa.Integer(), server_default="0", nullable=False),
        sa.Column("critical_path_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["repo_id"], ["repos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repo_id", "node_id", name="uq_impact_metrics_repo_node"),
    )
    op.create_index("ix_impact_metrics_repo_id", "impact_metrics", ["repo_id"])
    op.create_index("ix_impact_metrics_centrality", "impact_metrics", ["repo_id", "centrality_score"])


def downgrade() -> None:
    op.drop_index("ix_impact_metrics_centrality", table_name="impact_metrics")
    op.drop_index("ix_impact_metrics_repo_id", table_name="impact_metrics")
    op.drop_table("impact_metrics")
    op.drop_index("ix_critical_paths_repo_id", table_name="critical_paths")
    op.drop_table("critical_paths")
    op.drop_index("ix_blast_radius_cache_expires", table_name="blast_radius_cache")
    op.drop_index("ix_blast_radius_cache_lookup", table_name="blast_radius_cache")
    op.drop_table("blast_radius_cache")
