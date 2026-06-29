import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.repo import Repo


class ImpactAnalysis(Base):
    __tablename__ = "impact_analyses"

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
    node_id: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    node_name: Mapped[str] = mapped_column(String(500), nullable=False)
    node_type: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)
    blast_radius: Mapped[int] = mapped_column(Integer, nullable=False)
    affected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    effort_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recommendations: Mapped[list[dict]] = mapped_column(JSONB, default=list, server_default="[]")
    graph_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    repo: Mapped["Repo"] = relationship("Repo")

    def __repr__(self) -> str:
        return f"<ImpactAnalysis(id={self.id}, node_name={self.node_name!r}, risk_level={self.risk_level!r})>"
