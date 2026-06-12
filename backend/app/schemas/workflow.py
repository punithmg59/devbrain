"""Workflow intelligence API schemas."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkflowNodeRef(BaseModel):
    node_id: str
    name: str
    node_type: str
    file_path: str
    relationship_type: str = "member"


class WorkflowApiRef(BaseModel):
    api_route: str
    method: Optional[str] = None


class WorkflowSummary(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    criticality: str
    workflow_type: str
    confidence: float
    service_name: Optional[str] = None
    node_count: int = 0
    api_count: int = 0


class WorkflowDetail(WorkflowSummary):
    reasoning: Optional[str] = None
    source_evidence: Optional[dict[str, Any]] = None
    nodes: List[WorkflowNodeRef] = Field(default_factory=list)
    apis: List[WorkflowApiRef] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    files: List[str] = Field(default_factory=list)
    related_workflows: List[str] = Field(default_factory=list)
    user_journeys: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WorkflowListResponse(BaseModel):
    workflows: List[WorkflowSummary]
    total: int


class DiscoverWorkflowsResponse(BaseModel):
    discovered: int
    workflows: List[WorkflowSummary]
    message: str


class WorkflowFeedbackRequest(BaseModel):
    query: str
    workflow_id: str
    accepted: bool = False
    rejected: bool = False


class WorkflowFeedbackResponse(BaseModel):
    ok: bool
    workflow_id: str
    new_confidence: Optional[float] = None
    message: str


class WorkflowEvidenceStep(BaseModel):
    label: str
    step_type: str = "node"


class WorkflowEvidenceChain(BaseModel):
    steps: List[WorkflowEvidenceStep] = Field(default_factory=list)
    confidence: float = 0.0
    summary: str = ""
