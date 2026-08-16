"""add_has_completed_analysis

Revision ID: m3n4o5p6q7r8
Revises: k1l2m3n4o5p6
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m3n4o5p6q7r8"
down_revision: Union[str, None] = "k1l2m3n4o5p6_encrypted"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('repos', sa.Column('has_completed_analysis', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('repos', 'has_completed_analysis')
