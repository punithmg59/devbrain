"""ai function intelligence

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "g7h8i9j0k1l2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "nodes",
        sa.Column("detailed_explanation", sa.Text(), nullable=True),
    )
    op.add_column(
        "nodes",
        sa.Column("architecture_role", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "nodes",
        sa.Column("complexity_level", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "nodes",
        sa.Column("call_flow_diagram", sa.Text(), nullable=True),
    )
    op.add_column(
        "nodes",
        sa.Column("ai_tags", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "nodes",
        sa.Column("potential_risks", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("nodes", "potential_risks")
    op.drop_column("nodes", "ai_tags")
    op.drop_column("nodes", "call_flow_diagram")
    op.drop_column("nodes", "complexity_level")
    op.drop_column("nodes", "architecture_role")
    op.drop_column("nodes", "detailed_explanation")
