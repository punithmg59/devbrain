from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from app.models.intent import Intent


class EvidenceRequest(BaseModel):
    """Request schema for evidence collection."""
    
    intent: Intent = Field(..., description="The classified intent")
    repo_id: UUID = Field(..., description="Repository ID")
    target: str = Field(..., description="Target name (e.g., 'AuthService', 'User model')")
    target_type: Optional[str] = Field(None, description="Target type (e.g., 'service', 'model')")
    max_results: int = Field(50, ge=1, le=200, description="Maximum results per evidence type")
    include_code_snippets: bool = Field(True, description="Include code snippets in evidence")


class NodeEvidence(BaseModel):
    """Evidence for a single node."""
    
    id: UUID
    name: str
    node_type: str
    full_path: str
    signature: Optional[str] = None
    raw_code: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    complexity_score: float = 0.0
    architecture_role: Optional[str] = None
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance to the query")


class EdgeEvidence(BaseModel):
    """Evidence for a relationship edge."""
    
    id: UUID
    from_node_name: str
    to_node_name: str
    edge_type: str
    weight: float
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance to the query")


class WorkflowEvidence(BaseModel):
    """Evidence for a workflow."""
    
    id: UUID
    name: str
    workflow_type: str
    criticality: str
    confidence: float
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance to the query")


class EvidenceResponse(BaseModel):
    """Response schema for evidence collection."""
    
    intent: Intent
    target: str
    target_node: Optional[NodeEvidence] = None
    
    # Direct relationships
    affected_functions: List[NodeEvidence] = Field(default_factory=list)
    affected_services: List[NodeEvidence] = Field(default_factory=list)
    affected_apis: List[NodeEvidence] = Field(default_factory=list)
    affected_database_tables: List[NodeEvidence] = Field(default_factory=list)
    
    # Call graph
    callers: List[NodeEvidence] = Field(default_factory=list)
    callees: List[NodeEvidence] = Field(default_factory=list)
    
    # Dependencies
    imports: List[str] = Field(default_factory=list)
    dependencies: List[NodeEvidence] = Field(default_factory=list)
    dependents: List[NodeEvidence] = Field(default_factory=list)
    
    # Higher-level structures
    critical_paths: List[List[NodeEvidence]] = Field(default_factory=list)
    workflows: List[WorkflowEvidence] = Field(default_factory=list)
    
    # Metadata
    total_nodes_analyzed: int = 0
    collection_method: str = Field(..., description="Method used: 'graph_traversal', 'semantic_search', etc.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in evidence quality")
