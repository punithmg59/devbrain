import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.edge import Edge
    from app.models.file import RepoFile
    from app.models.repo import Repo


class Node(Base):
    __tablename__ = "nodes"
    __table_args__ = (UniqueConstraint("repo_id", "full_path", name="uq_nodes_repo_id_full_path"),)

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
    file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_files.id"),
        nullable=True,
        index=True,
    )
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(1000), nullable=False)
    full_path: Mapped[str] = mapped_column(String(2000), nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    calls: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    called_by: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    imports: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    http_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    route_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    detailed_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    architecture_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    complexity_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    call_flow_diagram: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_tags: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    potential_risks: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    is_exported: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_async: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    complexity_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    fan_in: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    fan_out: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    blast_radius: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    coupling_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    risk_level: Mapped[str] = mapped_column(String(20), default="low", server_default="low")
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

    repo: Mapped["Repo"] = relationship("Repo", back_populates="nodes")
    file: Mapped["RepoFile | None"] = relationship("RepoFile", back_populates="nodes")
    outgoing_edges: Mapped[list["Edge"]] = relationship(
        "Edge",
        foreign_keys="Edge.from_node_id",
        back_populates="from_node",
    )
    incoming_edges: Mapped[list["Edge"]] = relationship(
        "Edge",
        foreign_keys="Edge.to_node_id",
        back_populates="to_node",
    )

    def __repr__(self) -> str:
        return f"<Node(id={self.id}, name={self.name!r}, type={self.node_type!r})>"
