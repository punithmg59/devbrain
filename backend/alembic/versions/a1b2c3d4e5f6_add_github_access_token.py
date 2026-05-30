"""add github_access_token to users

Revision ID: a1b2c3d4e5f6
Revises: 28d48d8806db
Create Date: 2026-05-30 12:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "28d48d8806db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("github_access_token", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "github_access_token")
