import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Alias(Base):
    __tablename__ = "aliases"
    __table_args__ = (
        UniqueConstraint("repo_id", "alias", "node_id", name="uq_aliases_repo_alias_node"),
    )

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
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=True,
    )
    file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_files.id", ondelete="CASCADE"),
        nullable=True,
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    alias: Mapped[str] = mapped_column(String(500), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, server_default="1.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
