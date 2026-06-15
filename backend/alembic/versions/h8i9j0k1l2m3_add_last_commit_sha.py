"""add_last_commit_sha

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-06-14 19:04:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('repos', sa.Column('last_commit_sha', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_repos_last_commit_sha'), 'repos', ['last_commit_sha'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_repos_last_commit_sha'), table_name='repos')
    op.drop_column('repos', 'last_commit_sha')
