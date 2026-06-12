"""smart resolver: aliases, resolver_logs, node embeddings, pg_trgm

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-31 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "aliases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("alias", sa.String(length=500), nullable=False),
        sa.Column("weight", sa.Float(), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["repo_id"], ["repos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["repo_files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repo_id", "alias", "node_id", name="uq_aliases_repo_alias_node"),
    )
    op.create_index("ix_aliases_repo_id", "aliases", ["repo_id"])
    op.create_index("ix_aliases_alias_trgm", "aliases", ["alias"], postgresql_using="gin", postgresql_ops={"alias": "gin_trgm_ops"})

    op.create_table(
        "resolver_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("top_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("top_entity_name", sa.String(length=1000), nullable=True),
        sa.Column("top_confidence", sa.Integer(), nullable=True),
        sa.Column("candidate_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("resolution_ms", sa.Integer(), nullable=True),
        sa.Column("candidates_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["repo_id"], ["repos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resolver_logs_repo_created", "resolver_logs", ["repo_id", "created_at"])

    op.create_table(
        "node_embeddings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("embedding", postgresql.JSONB(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["repo_id"], ["repos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repo_id", "node_id", name="uq_node_embeddings_repo_node"),
    )
    op.create_index("ix_node_embeddings_repo", "node_embeddings", ["repo_id"])

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_nodes_name_trgm ON nodes USING gin (name gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_nodes_name_trgm")
    op.drop_table("node_embeddings")
    op.drop_table("resolver_logs")
    op.drop_index("ix_aliases_alias_trgm", table_name="aliases")
    op.drop_index("ix_aliases_repo_id", table_name="aliases")
    op.drop_table("aliases")
