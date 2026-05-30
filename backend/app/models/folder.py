import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.repo import Repo


class FolderTree(Base):
    __tablename__ = "folder_tree"
    __table_args__ = (
        UniqueConstraint("repo_id", "folder_path", name="uq_folder_tree_repo_id_folder_path"),
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
    folder_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    folder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    depth: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    file_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    function_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    repo: Mapped["Repo"] = relationship("Repo", back_populates="folders")

    def __repr__(self) -> str:
        return f"<FolderTree(id={self.id}, folder_path={self.folder_path!r})>"
