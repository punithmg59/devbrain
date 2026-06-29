import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


STAGES = [
    "queued", 
    "cloning", 
    "scanning", 
    "parsing", 
    "building_graph", 
    "saving"
]
TERMINAL = {"completed", "completed_with_warnings", "failed"}


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(40), default="queued", server_default="queued", index=True
    )
    current_stage: Mapped[str] = mapped_column(
        String(40), default="queued", server_default="queued"
    )   
    progress_percent: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0.0"
    )
    files_total: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    files_processed: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    functions_found: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    nodes_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    edges_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    files_failed: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    duration_seconds: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    files_per_second: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    nodes_per_second: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    edges_per_second: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    fast_mode: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    incremental: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    warnings: Mapped[list] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    worker_id: Mapped[str | None] = mapped_column(
        String(80), nullable=True
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class FileError(Base):
    __tablename__ = "file_errors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(
        String(1000), nullable=False
    )
    error_type: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
    message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
