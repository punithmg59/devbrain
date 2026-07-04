from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from app.models.intent import Intent
from app.schemas.evidence import EvidenceResponse, NodeEvidence, WorkflowEvidence


class ImpactAnalysisRequest(BaseModel):
    """Request schema for impact analysis."""
    
    intent: Intent = Field(..., description="The classified intent")
    repo_id: UUID = Field(..., description="Repository ID")
    target: str = Field(..., description="Target name")
    target_node_id: Optional[UUID] = Field(None, description="Target node ID if known")
    evidence: Optional[EvidenceResponse] = Field(None, description="Repository evidence from Evidence Engine")
    max_depth: int = Field(5, ge=1, le=10, description="Maximum traversal depth for blast radius")
    include_indirect: bool = Field(True, description="Include indirect dependencies")


class AffectedEntity(BaseModel):
    """An entity affected by the change."""
    
    id: UUID
    name: str
    entity_type: str  # service, api, database, function, etc.
    impact_level: str = Field(..., description="critical, high, medium, low")
    dependency_distance: int = Field(..., description="Distance from target in dependency graph")
    is_direct: bool = Field(..., description="Whether this is a direct dependency")
    risk_contribution: float = Field(..., ge=0.0, le=1.0, description="Contribution to overall risk")


class BlastRadiusResult(BaseModel):
    """Blast radius calculation result."""
    
    total_affected_entities: int
    direct_dependencies: int
    indirect_dependencies: int
    affected_services: List[AffectedEntity]
    affected_apis: List[AffectedEntity]
    affected_databases: List[AffectedEntity]
    affected_functions: List[AffectedEntity]
    max_depth_reached: int
    traversal_complete: bool


class ComplexityScore(BaseModel):
    """Engineering complexity score."""
    
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Overall complexity (0-100)")
    cyclomatic_complexity: float = Field(..., ge=0.0, le=100.0)
    dependency_complexity: float = Field(..., ge=0.0, le=100.0)
    coupling_complexity: float = Field(..., ge=0.0, le=100.0)
    data_complexity: float = Field(..., ge=0.0, le=100.0)
    control_flow_complexity: float = Field(..., ge=0.0, le=100.0)


class DifficultyScore(BaseModel):
    """Difficulty score for implementation."""
    
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Overall difficulty (0-100)")
    technical_difficulty: float = Field(..., ge=0.0, le=100.0)
    testing_difficulty: float = Field(..., ge=0.0, le=100.0)
    deployment_difficulty: float = Field(..., ge=0.0, le=100.0)
    migration_difficulty: float = Field(..., ge=0.0, le=100.0)
    rollback_difficulty: float = Field(..., ge=0.0, le=100.0)


class ChangeStep(BaseModel):
    """A single step in the recommended change order."""
    
    step_number: int
    entity_id: UUID
    entity_name: str
    entity_type: str
    action: str = Field(..., description="delete, modify, add, etc.")
    dependencies: List[UUID] = Field(default_factory=list, description="IDs of entities this depends on")
    estimated_effort_hours: float = Field(..., ge=0.0)
    risk_level: str = Field(..., description="critical, high, medium, low")
    blocking_for: List[UUID] = Field(default_factory=list, description="IDs of entities blocked by this step")


class RiskScore(BaseModel):
    """Risk score breakdown."""
    
    overall_risk_score: float = Field(..., ge=0.0, le=100.0, description="Overall risk (0-100)")
    risk_category: str = Field(..., description="critical, high, medium, low, safe")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in risk assessment")
    
    # Risk factors
    blast_radius_risk: float = Field(..., ge=0.0, le=100.0)
    dependency_risk: float = Field(..., ge=0.0, le=100.0)
    complexity_risk: float = Field(..., ge=0.0, le=100.0)
    workflow_risk: float = Field(..., ge=0.0, le=100.0)
    api_risk: float = Field(..., ge=0.0, le=100.0)
    database_risk: float = Field(..., ge=0.0, le=100.0)
    
    # Risk factors detail
    risk_factors: Dict[str, float] = Field(default_factory=dict)


class ImpactAnalysisResponse(BaseModel):
    """Response schema for impact analysis."""
    
    intent: Intent
    target: str
    target_node_id: Optional[UUID]
    
    # Risk assessment
    risk_score: RiskScore
    
    # Blast radius
    blast_radius: BlastRadiusResult
    
    # Breaking changes
    breaking_apis: List[AffectedEntity]
    breaking_services: List[AffectedEntity]
    breaking_databases: List[AffectedEntity]
    
    # Affected entities
    affected_services: List[AffectedEntity]
    affected_databases: List[AffectedEntity]
    affected_workflows: List[WorkflowEvidence]
    
    # Complexity and difficulty
    engineering_complexity: ComplexityScore
    migration_difficulty: DifficultyScore
    implementation_difficulty: DifficultyScore
    
    # Change plan
    recommended_change_order: List[ChangeStep]
    total_estimated_effort_hours: float
    
    # Metadata
    analysis_method: str = Field(..., description="Method used: graph_traversal, dependency_analysis, etc.")
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")
    nodes_analyzed: int = Field(..., description="Total nodes analyzed")
    edges_traversed: int = Field(..., description="Total edges traversed")
