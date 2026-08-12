import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, DialectUUID

if TYPE_CHECKING:
    from app.models.node import Node
    from app.models.repo import Repo


class RepoFile(Base):
    __tablename__ = "repo_files"
    __table_args__ = (UniqueConstraint("repo_id", "file_path", name="uq_repo_files_repo_id_file_path"),)

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
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language: Mapped[str | None] = mapped_column(String(100), nullable=True)
    folder_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    depth: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    line_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    content_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_preview_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    importance_score: Mapped[float] = mapped_column(Float, default=0.5, server_default="0.5")
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    last_commit_sha: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    last_analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    repo: Mapped["Repo"] = relationship("Repo", back_populates="files")
    nodes: Mapped[list["Node"]] = relationship("Node", back_populates="file")

    def __repr__(self) -> str:
        return f"<RepoFile(id={self.id}, file_path={self.file_path!r})>"
