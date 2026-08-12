"""Workflow intelligence ORM models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, DialectJSON, DialectUUID


class Workflow(Base):
    __tablename__ = "workflows"
    __table_args__ = (UniqueConstraint("repo_id", "name", name="uq_workflows_repo_name"),)

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
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    criticality: Mapped[str] = mapped_column(String(32), server_default="medium", nullable=False)
    workflow_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, server_default="0.0", nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_evidence: Mapped[dict[str, Any] | None] = mapped_column(DialectJSON(), nullable=True)
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

    nodes: Mapped[list["WorkflowNode"]] = relationship(
        "WorkflowNode", back_populates="workflow", cascade="all, delete-orphan"
    )
    files: Mapped[list["WorkflowFile"]] = relationship(
        "WorkflowFile", back_populates="workflow", cascade="all, delete-orphan"
    )
    apis: Mapped[list["WorkflowApi"]] = relationship(
        "WorkflowApi", back_populates="workflow", cascade="all, delete-orphan"
    )
    services: Mapped[list["WorkflowService"]] = relationship(
        "WorkflowService", back_populates="workflow", cascade="all, delete-orphan"
    )


class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"
    __table_args__ = (UniqueConstraint("workflow_id", "node_id", name="uq_workflow_nodes_wf_node"),)

    id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(String(64), server_default="member", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="nodes")


class WorkflowFile(Base):
    __tablename__ = "workflow_files"
    __table_args__ = (UniqueConstraint("workflow_id", "file_id", name="uq_workflow_files_wf_file"),)

    id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        ForeignKey("repo_files.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="files")


class WorkflowApi(Base):
    __tablename__ = "workflow_apis"
    __table_args__ = (UniqueConstraint("workflow_id", "api_route", name="uq_workflow_apis_wf_route"),)

    id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    api_route: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="apis")


class WorkflowService(Base):
    __tablename__ = "workflow_services"
    __table_args__ = (
        UniqueConstraint("workflow_id", "service_name", name="uq_workflow_services_wf_svc"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        DialectUUID(),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="services")


class WorkflowFeedback(Base):
    __tablename__ = "workflow_feedback"

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
    query: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        DialectUUID(),
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
    )
    accepted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    rejected: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
