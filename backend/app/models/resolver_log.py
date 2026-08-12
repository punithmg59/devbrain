import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, DialectJSON, DialectUUID


class ResolverLog(Base):
    __tablename__ = "resolver_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    repo_id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        ForeignKey("repos.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        DialectUUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    top_entity_id: Mapped[uuid.UUID | None] = mapped_column(DialectUUID(), nullable=True)
    top_entity_name: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    top_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    resolution_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidates_json: Mapped[dict | None] = mapped_column(DialectJSON(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
