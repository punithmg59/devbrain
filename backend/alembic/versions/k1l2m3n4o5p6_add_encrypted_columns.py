"""add_encrypted_columns

Revision ID: k1l2m3n4o5p6
Revises: i9j0k1l2m3n4
Create Date: 2026-08-11 00:00:00.000000

This migration adds encrypted columns for sensitive data:
- repo_files.content_preview_encrypted (for file content previews)
- nodes.raw_code_encrypted (for source code snippets)

These columns will store AES-256-GCM encrypted data while the original
plaintext columns will be phased out.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k1l2m3n4o5p6_encrypted"
down_revision: Union[str, None] = "i9j0k1l2m3n4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add encrypted column for file content previews
    op.add_column('repo_files', sa.Column('content_preview_encrypted', sa.Text(), nullable=True))
    
    # Add encrypted column for node raw code
    op.add_column('nodes', sa.Column('raw_code_encrypted', sa.Text(), nullable=True))
    
    # Create indexes for encrypted columns to improve query performance
    # Note: These indexes will be on the encrypted data, not searchable content
    op.create_index('ix_repo_files_content_preview_encrypted', 'repo_files', ['content_preview_encrypted'])
    op.create_index('ix_nodes_raw_code_encrypted', 'nodes', ['raw_code_encrypted'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_nodes_raw_code_encrypted', table_name='nodes')
    op.drop_index('ix_repo_files_content_preview_encrypted', table_name='repo_files')
    
    # Drop encrypted columns
    op.drop_column('nodes', 'raw_code_encrypted')
    op.drop_column('repo_files', 'content_preview_encrypted')
