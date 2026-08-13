"""Explainable risk engine persistence models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, DialectJSON, DialectUUID


class RiskProfile(Base):
    __tablename__ = "risk_profiles"
    __table_args__ = (
        UniqueConstraint("repo_id", "entity_type", "entity_id", name="uq_risk_profiles_repo_entity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        ForeignKey("repos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        nullable=False,
    )
    risk_score: Mapped[float] = mapped_column(Float, server_default="0.0", nullable=False)
    risk_category: Mapped[str] = mapped_column(Text, server_default="safe", nullable=False)
    risk_factors: Mapped[dict[str, Any]] = mapped_column(DialectJSON(), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, server_default="0.0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"), nullable=False
    )


class RiskBreakdown(Base):
    __tablename__ = "risk_breakdowns"

    id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        ForeignKey("repos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        nullable=False,
    )
    factor_name: Mapped[str] = mapped_column(Text, nullable=False)
    factor_score: Mapped[float] = mapped_column(Float, server_default="0.0", nullable=False)
    weight: Mapped[float] = mapped_column(Float, server_default="0.0", nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(DialectJSON(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


class RiskHistory(Base):
    __tablename__ = "risk_history"

    id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        ForeignKey("repos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        nullable=False,
    )
    previous_score: Mapped[float] = mapped_column(Float, server_default="0.0", nullable=False)
    new_score: Mapped[float] = mapped_column(Float, server_default="0.0", nullable=False)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
