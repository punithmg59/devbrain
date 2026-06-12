"""Blast radius intelligence ORM models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BlastRadiusCache(Base):
    __tablename__ = "blast_radius_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repos.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CriticalPath(Base):
    __tablename__ = "critical_paths"
    __table_args__ = (UniqueConstraint("repo_id", "name", name="uq_critical_paths_repo_name"),)

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
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    criticality: Mapped[str] = mapped_column(String(32), server_default="high", nullable=False)
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
    )
    path_nodes: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ImpactMetric(Base):
    __tablename__ = "impact_metrics"
    __table_args__ = (UniqueConstraint("repo_id", "node_id", name="uq_impact_metrics_repo_node"),)

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
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    dependency_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    workflow_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    service_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    api_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    journey_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    centrality_score: Mapped[float] = mapped_column(Float, server_default="0.0", nullable=False)
    blast_radius_score: Mapped[float] = mapped_column(Float, server_default="0.0", nullable=False)
    in_degree: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    out_degree: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    critical_path_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
