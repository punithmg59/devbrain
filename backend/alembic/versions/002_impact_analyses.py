"""impact_analyses

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-06-29 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'k1l2m3n4o5p6'
down_revision: Union[str, None] = 'j0k1l2m3n4o5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'impact_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('repo_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('node_id', sa.String(length=500), nullable=False),
        sa.Column('node_name', sa.String(length=500), nullable=False),
        sa.Column('node_type', sa.String(length=100), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('risk_level', sa.String(length=50), nullable=False),
        sa.Column('blast_radius', sa.Integer(), nullable=False),
        sa.Column('affected_count', sa.Integer(), nullable=False),
        sa.Column('effort_label', sa.String(length=100), nullable=True),
        sa.Column('recommendations', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('graph_data', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['repo_id'], ['repos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_impact_analyses_repo_id', 'impact_analyses', ['repo_id'], unique=False)
    op.create_index('ix_impact_analyses_node_id', 'impact_analyses', ['node_id'], unique=False)
    op.create_index('ix_impact_analyses_created_at', 'impact_analyses', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_impact_analyses_created_at', table_name='impact_analyses')
    op.drop_index('ix_impact_analyses_node_id', table_name='impact_analyses')
    op.drop_index('ix_impact_analyses_repo_id', table_name='impact_analyses')
    op.drop_table('impact_analyses')
