from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from app.models.intent import Intent
from app.schemas.evidence import EvidenceResponse
from app.schemas.impact_analysis import ImpactAnalysisResponse


class RecommendationRequest(BaseModel):
    """Request schema for recommendation generation."""
    
    intent: Intent = Field(..., description="The classified intent")
    repo_id: UUID = Field(..., description="Repository ID")
    target: str = Field(..., description="Target name")
    evidence: Optional[EvidenceResponse] = Field(None, description="Repository evidence from Evidence Engine")
    impact: Optional[ImpactAnalysisResponse] = Field(None, description="Impact analysis from Impact Analysis Engine")
    include_rollback: bool = Field(True, description="Include rollback plan in recommendations")
    include_tests: bool = Field(True, description="Include test recommendations")


class Recommendation(BaseModel):
    """A single recommendation."""
    
    id: str = Field(..., description="Unique identifier for this recommendation")
    type: str = Field(..., description="delete_order, refactor, api_update, test, workflow, migration, rollback")
    priority: str = Field(..., description="critical, high, medium, low")
    title: str = Field(..., description="Human-readable title")
    description: str = Field(..., description="Detailed description")
    entity_id: Optional[UUID] = Field(None, description="Related entity ID if applicable")
    entity_name: Optional[str] = Field(None, description="Related entity name if applicable")
    entity_type: Optional[str] = Field(None, description="Related entity type if applicable")
    action: str = Field(..., description="Specific action to take")
    estimated_effort_hours: float = Field(..., ge=0.0, description="Estimated effort in hours")
    dependencies: List[str] = Field(default_factory=list, description="IDs of recommendations this depends on")
    risk_level: str = Field(..., description="critical, high, medium, low")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this recommendation")


class DeleteOrderRecommendation(BaseModel):
    """Recommendation for delete order."""
    
    step_number: int
    entity_id: UUID
    entity_name: str
    entity_type: str
    reason: str = Field(..., description="Why this should be deleted at this step")
    blocking_for: List[UUID] = Field(default_factory=list, description="Entities blocked by this deletion")
    safe_to_delete: bool = Field(..., description="Whether it's safe to delete this entity")
    rollback_action: str = Field(..., description="Action to rollback this deletion")


class RefactorRecommendation(BaseModel):
    """Recommendation for refactoring."""
    
    file_id: Optional[UUID] = Field(None, description="File to refactor")
    file_path: str = Field(..., description="File path to refactor")
    refactor_type: str = Field(..., description="extract_method, rename, simplify, etc.")
    current_complexity: float = Field(..., description="Current complexity score")
    target_complexity: float = Field(..., description="Target complexity after refactor")
    reason: str = Field(..., description="Why this refactoring is recommended")
    estimated_lines_changed: int = Field(..., description="Estimated lines of code to change")


class TestRecommendation(BaseModel):
    """Recommendation for testing."""
    
    test_type: str = Field(..., description="unit, integration, e2e, regression")
    target_entity_id: Optional[UUID] = Field(None, description="Entity to test")
    target_entity_name: str = Field(..., description="Entity name to test")
    test_framework: str = Field(..., description="pytest, jest, etc.")
    coverage_target: float = Field(..., ge=0.0, le=1.0, description="Target coverage percentage")
    priority: str = Field(..., description="critical, high, medium, low")
    reason: str = Field(..., description="Why this test is needed")


class WorkflowRecommendation(BaseModel):
    """Recommendation for workflow review."""
    
    workflow_id: UUID
    workflow_name: str
    action: str = Field(..., description="review, update, document, etc.")
    reason: str = Field(..., description="Why this workflow needs attention")
    affected_apis: List[str] = Field(default_factory=list, description="APIs in this workflow")
    affected_services: List[str] = Field(default_factory=list, description="Services in this workflow")


class MigrationRecommendation(BaseModel):
    """Recommendation for database migration."""
    
    migration_type: str = Field(..., description="create_table, alter_table, drop_table, etc.")
    table_name: str = Field(..., description="Table name")
    description: str = Field(..., description="Migration description")
    is_destructive: bool = Field(..., description="Whether this migration is destructive")
    requires_downtime: bool = Field(..., description="Whether this requires downtime")
    rollback_migration: Optional[str] = Field(None, description="SQL to rollback this migration")


class RollbackStep(BaseModel):
    """A single step in a rollback plan."""
    
    step_number: int
    action: str = Field(..., description="restore, revert, disable, etc.")
    target: str = Field(..., description="Target of this rollback step")
    command: str = Field(..., description="Command or action to execute")
    estimated_time_seconds: int = Field(..., description="Estimated time to execute")
    verification: str = Field(..., description="How to verify this step succeeded")


class RollbackPlan(BaseModel):
    """Complete rollback plan."""
    
    plan_id: str = Field(..., description="Unique identifier for this plan")
    total_steps: int = Field(..., description="Total number of rollback steps")
    total_estimated_time_seconds: int = Field(..., description="Total estimated rollback time")
    steps: List[RollbackStep] = Field(..., description="Rollback steps in order")
    can_rollback_automatically: bool = Field(..., description="Whether rollback can be automated")
    manual_intervention_required: bool = Field(..., description="Whether manual intervention is required")
    data_loss_risk: str = Field(..., description="none, low, medium, high")


class RecommendationResponse(BaseModel):
    """Response schema for recommendation generation."""
    
    intent: Intent
    target: str
    recommendations: List[Recommendation] = Field(..., description="All recommendations")
    
    # Specific recommendation types
    delete_order: List[DeleteOrderRecommendation] = Field(default_factory=list)
    refactor_recommendations: List[RefactorRecommendation] = Field(default_factory=list)
    test_recommendations: List[TestRecommendation] = Field(default_factory=list)
    workflow_recommendations: List[WorkflowRecommendation] = Field(default_factory=list)
    migration_recommendations: List[MigrationRecommendation] = Field(default_factory=list)
    
    # Rollback plan
    rollback_plan: Optional[RollbackPlan] = Field(None, description="Rollback plan if requested")
    
    # Summary
    total_recommendations: int = Field(..., description="Total number of recommendations")
    critical_count: int = Field(..., description="Number of critical recommendations")
    high_count: int = Field(..., description="Number of high priority recommendations")
    total_estimated_effort_hours: float = Field(..., description="Total estimated effort")
    
    # Metadata
    generation_method: str = Field(..., description="Method used: deterministic, rule_based, etc.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in recommendations")
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")
