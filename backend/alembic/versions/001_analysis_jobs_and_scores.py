"""analysis_jobs_and_scores

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-06-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'j0k1l2m3n4o5'
down_revision: Union[str, None] = 'i9j0k1l2m3n4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create table analysis_jobs
    op.create_table(
        'analysis_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('repo_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=40), server_default='queued', nullable=False),
        sa.Column('current_stage', sa.String(length=40), server_default='queued', nullable=False),
        sa.Column('progress_percent', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('files_total', sa.Integer(), server_default='0', nullable=False),
        sa.Column('files_processed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('functions_found', sa.Integer(), server_default='0', nullable=False),
        sa.Column('nodes_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('edges_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('files_failed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('files_per_second', sa.Float(), nullable=True),
        sa.Column('nodes_per_second', sa.Float(), nullable=True),
        sa.Column('edges_per_second', sa.Float(), nullable=True),
        sa.Column('fast_mode', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('incremental', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('worker_id', sa.String(length=80), nullable=True),
        sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['repo_id'], ['repos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_analysis_jobs_repo_id', 'analysis_jobs', ['repo_id'], unique=False)
    op.create_index('ix_analysis_jobs_status', 'analysis_jobs', ['status'], unique=False)

    # 2. Create table file_errors
    op.create_table(
        'file_errors',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('repo_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_path', sa.String(length=1000), nullable=False),
        sa.Column('error_type', sa.String(length=120), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['analysis_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['repo_id'], ['repos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_file_errors_job_id', 'file_errors', ['job_id'], unique=False)

    # 3. Add column content_hash to repos table
    op.add_column('repos', sa.Column('content_hash', sa.String(length=64), nullable=True))

    # 4. Add column content_hash to repo_files table
    op.add_column('repo_files', sa.Column('content_hash', sa.String(length=64), nullable=True))
    op.create_index('ix_repo_files_content_hash', 'repo_files', ['content_hash'], unique=False)

    # 5. Add column last_commit_sha to repo_files table
    op.add_column('repo_files', sa.Column('last_commit_sha', sa.String(length=100), nullable=True))

    # 6. Add column last_analyzed_at to repo_files table
    op.add_column('repo_files', sa.Column('last_analyzed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # 6. Reverse
    op.drop_column('repo_files', 'last_analyzed_at')

    # 5. Reverse
    op.drop_column('repo_files', 'last_commit_sha')

    # 4. Reverse
    op.drop_index('ix_repo_files_content_hash', table_name='repo_files')
    op.drop_column('repo_files', 'content_hash')

    # 3. Reverse
    op.drop_column('repos', 'content_hash')

    # 2. Reverse
    op.drop_index('ix_file_errors_job_id', table_name='file_errors')
    op.drop_table('file_errors')

    # 1. Reverse
    op.drop_index('ix_analysis_jobs_status', table_name='analysis_jobs')
    op.drop_index('ix_analysis_jobs_repo_id', table_name='analysis_jobs')
    op.drop_table('analysis_jobs')
