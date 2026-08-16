import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, DialectUUID

if TYPE_CHECKING:
    from app.models.edge import Edge
    from app.models.file import RepoFile
    from app.models.folder import FolderTree
    from app.models.node import Node
    from app.models.user import User


class Repo(Base):
    __tablename__ = "repos"

    id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    github_repo_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(500), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_branch: Mapped[str] = mapped_column(String(100), default="main", server_default="main")
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    language: Mapped[str | None] = mapped_column(String(100), nullable=True)
    analysis_status: Mapped[str] = mapped_column(
        String(50), default="pending", server_default="pending"
    )
    last_commit_sha: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    failure_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    has_completed_analysis: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    total_files: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_functions: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_lines: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
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

    user: Mapped["User"] = relationship("User", back_populates="repos")
    files: Mapped[list["RepoFile"]] = relationship(
        "RepoFile", back_populates="repo", cascade="all, delete-orphan"
    )
    nodes: Mapped[list["Node"]] = relationship(
        "Node", back_populates="repo", cascade="all, delete-orphan"
    )
    edges: Mapped[list["Edge"]] = relationship(
        "Edge", back_populates="repo", cascade="all, delete-orphan"
    )
    folders: Mapped[list["FolderTree"]] = relationship(
        "FolderTree", back_populates="repo", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Repo(id={self.id}, full_name={self.full_name!r}, status={self.analysis_status!r})>"
