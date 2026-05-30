"""initial_schema

Revision ID: 28d48d8806db
Revises:
Create Date: 2026-05-30 10:52:26.180341

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "28d48d8806db"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("github_id", sa.String(length=100), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("plan", sa.String(length=50), server_default="FREE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("github_id"),
    )
    op.create_index(op.f("ix_users_github_id"), "users", ["github_id"], unique=False)

    op.create_table(
        "repos",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("github_repo_id", sa.BigInteger(), nullable=False),
        sa.Column("full_name", sa.String(length=500), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_branch", sa.String(length=100), server_default="main", nullable=False),
        sa.Column("is_private", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("language", sa.String(length=100), nullable=True),
        sa.Column("analysis_status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("last_analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_files", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_functions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_lines", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("github_repo_id"),
    )
    op.create_index(op.f("ix_repos_user_id"), "repos", ["user_id"], unique=False)

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(length=500), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(op.f("ix_sessions_token"), "sessions", ["token"], unique=False)
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)

    op.create_table(
        "repo_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("extension", sa.String(length=50), nullable=True),
        sa.Column("language", sa.String(length=100), nullable=True),
        sa.Column("folder_path", sa.String(length=1000), nullable=False),
        sa.Column("depth", sa.Integer(), server_default="0", nullable=False),
        sa.Column("size_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("line_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("content_preview", sa.Text(), nullable=True),
        sa.Column("s3_key", sa.String(length=500), nullable=True),
        sa.Column("importance_score", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["repo_id"], ["repos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repo_id", "file_path", name="uq_repo_files_repo_id_file_path"),
    )
    op.create_index(op.f("ix_repo_files_repo_id"), "repo_files", ["repo_id"], unique=False)

    op.create_table(
        "folder_tree",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("folder_path", sa.String(length=1000), nullable=False),
        sa.Column("folder_name", sa.String(length=255), nullable=False),
        sa.Column("parent_path", sa.String(length=1000), nullable=True),
        sa.Column("depth", sa.Integer(), server_default="0", nullable=False),
        sa.Column("file_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("function_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["repo_id"], ["repos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repo_id", "folder_path", name="uq_folder_tree_repo_id_folder_path"),
    )
    op.create_index(op.f("ix_folder_tree_repo_id"), "folder_tree", ["repo_id"], unique=False)

    op.create_table(
        "nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("node_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=1000), nullable=False),
        sa.Column("full_path", sa.String(length=2000), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=True),
        sa.Column("end_line", sa.Integer(), nullable=True),
        sa.Column("raw_code", sa.Text(), nullable=True),
        sa.Column("signature", sa.String(length=1000), nullable=True),
        sa.Column("calls", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("called_by", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("imports", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("http_method", sa.String(length=10), nullable=True),
        sa.Column("route_path", sa.String(length=500), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("is_exported", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_async", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("complexity_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["repo_files.id"]),
        sa.ForeignKeyConstraint(["repo_id"], ["repos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repo_id", "full_path", name="uq_nodes_repo_id_full_path"),
    )
    op.create_index(op.f("ix_nodes_file_id"), "nodes", ["file_id"], unique=False)
    op.create_index(op.f("ix_nodes_repo_id"), "nodes", ["repo_id"], unique=False)

    op.create_table(
        "edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_type", sa.String(length=50), nullable=False),
        sa.Column("weight", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["from_node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repo_id"], ["repos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_node_id", "to_node_id", "edge_type", name="uq_edges_from_to_type"),
    )
    op.create_index(op.f("ix_edges_from_node_id"), "edges", ["from_node_id"], unique=False)
    op.create_index(op.f("ix_edges_repo_id"), "edges", ["repo_id"], unique=False)
    op.create_index(op.f("ix_edges_to_node_id"), "edges", ["to_node_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_edges_to_node_id"), table_name="edges")
    op.drop_index(op.f("ix_edges_repo_id"), table_name="edges")
    op.drop_index(op.f("ix_edges_from_node_id"), table_name="edges")
    op.drop_table("edges")
    op.drop_index(op.f("ix_nodes_repo_id"), table_name="nodes")
    op.drop_index(op.f("ix_nodes_file_id"), table_name="nodes")
    op.drop_table("nodes")
    op.drop_index(op.f("ix_folder_tree_repo_id"), table_name="folder_tree")
    op.drop_table("folder_tree")
    op.drop_index(op.f("ix_repo_files_repo_id"), table_name="repo_files")
    op.drop_table("repo_files")
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_token"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_index(op.f("ix_repos_user_id"), table_name="repos")
    op.drop_table("repos")
    op.drop_index(op.f("ix_users_github_id"), table_name="users")
    op.drop_table("users")
