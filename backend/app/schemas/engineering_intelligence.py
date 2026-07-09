"""
Engineering Intelligence Schemas

Defines comprehensive response models for engineering intelligence.
All responses include engineering decisions, evidence, analysis, and actionable recommendations.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class EngineeringDecision(BaseModel):
    """The primary engineering decision based on analysis."""
    
    decision: str = Field(..., description="The engineering decision")
    rationale: str = Field(..., description="Rationale for the decision")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the decision")
    alternatives: List[str] = Field(default_factory=list, description="Alternative approaches considered")


class EngineeringEvidence(BaseModel):
    """Repository evidence supporting the engineering decision."""
    
    evidence_summary: str = Field(..., description="Summary of repository evidence")
    data_sources: List[str] = Field(default_factory=list, description="Data sources used")
    evidence_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the evidence")
    key_findings: List[str] = Field(default_factory=list, description="Key findings from repository analysis")


class RepositoryAnalysis(BaseModel):
    """Analysis of the repository structure and patterns."""
    
    structure_summary: str = Field(..., description="Summary of repository structure")
    patterns_identified: List[str] = Field(default_factory=list, description="Design patterns identified")
    code_metrics: Dict[str, Any] = Field(default_factory=dict, description="Code quality metrics")
    dependencies: List[str] = Field(default_factory=list, description="Key dependencies identified")


class AffectedComponent(BaseModel):
    """A component affected by the engineering change."""
    
    name: str = Field(..., description="Component name")
    type: str = Field(..., description="Component type (service, class, function, etc.)")
    file_path: str = Field(..., description="File path")
    impact_level: str = Field(..., description="Impact level (critical, high, medium, low)")
    impact_description: str = Field(..., description="Description of the impact")
    required_changes: List[str] = Field(default_factory=list, description="Required changes for this component")


class RiskAssessment(BaseModel):
    """Risk assessment for the engineering change."""
    
    overall_risk: str = Field(..., description="Overall risk level (critical, high, medium, low)")
    risk_factors: List[str] = Field(default_factory=list, description="Risk factors identified")
    probability_of_failure: float = Field(..., ge=0.0, le=1.0, description="Probability of failure")
    potential_impact: str = Field(..., description="Potential impact if failure occurs")
    mitigation_strategies: List[str] = Field(default_factory=list, description="Strategies to mitigate risks")


class RecommendedChange(BaseModel):
    """A recommended change to implement."""
    
    description: str = Field(..., description="Description of the change")
    priority: str = Field(..., description="Priority (critical, high, medium, low)")
    effort_estimate: str = Field(..., description="Effort estimate (e.g., '2-3 hours')")
    file_path: Optional[str] = Field(None, description="File path if applicable")
    line_number: Optional[int] = Field(None, description="Line number if applicable")
    code_snippet: Optional[str] = Field(None, description="Code snippet for the change")


class ImplementationStep(BaseModel):
    """A step in the implementation plan."""
    
    step_number: int = Field(..., description="Step number")
    description: str = Field(..., description="Description of the step")
    action_type: str = Field(..., description="Type of action (create, modify, delete, test)")
    target: str = Field(..., description="Target of the action")
    dependencies: List[str] = Field(default_factory=list, description="Dependencies on other steps")
    estimated_time: str = Field(..., description="Estimated time for the step")


class ImplementationPlan(BaseModel):
    """Comprehensive implementation plan."""
    
    phases: List[str] = Field(default_factory=list, description="Implementation phases")
    steps: List[ImplementationStep] = Field(default_factory=list, description="Detailed implementation steps")
    total_estimated_time: str = Field(..., description="Total estimated time")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisites for implementation")
    rollback_plan: str = Field(..., description="Rollback plan if issues occur")


class TestItem(BaseModel):
    """A test item in the testing checklist."""
    
    description: str = Field(..., description="Test description")
    test_type: str = Field(..., description="Test type (unit, integration, e2e, performance)")
    priority: str = Field(..., description="Test priority (critical, high, medium, low)")
    automated: bool = Field(..., description="Whether the test can be automated")
    test_scope: str = Field(..., description="Scope of the test")


class TestingChecklist(BaseModel):
    """Comprehensive testing checklist."""
    
    unit_tests: List[TestItem] = Field(default_factory=list, description="Unit tests to implement")
    integration_tests: List[TestItem] = Field(default_factory=list, description="Integration tests to implement")
    e2e_tests: List[TestItem] = Field(default_factory=list, description="End-to-end tests to implement")
    performance_tests: List[TestItem] = Field(default_factory=list, description="Performance tests to implement")
    security_tests: List[TestItem] = Field(default_factory=list, description="Security tests to implement")
    total_test_count: int = Field(default=0, description="Total number of tests")
    coverage_target: float = Field(..., ge=0.0, le=1.0, description="Target code coverage")


class EngineeringAction(BaseModel):
    """An actionable engineering step."""
    
    action_type: str = Field(..., description="Type of action (code, config, deployment, documentation)")
    description: str = Field(..., description="Description of the action")
    command: Optional[str] = Field(None, description="Command to execute if applicable")
    file_path: Optional[str] = Field(None, description="File path if applicable")
    priority: str = Field(..., description="Action priority")
    owner: Optional[str] = Field(None, description="Owner of the action")
    due_date: Optional[str] = Field(None, description="Due date for the action")


class EngineeringIntelligenceResponse(BaseModel):
    """
    Comprehensive engineering intelligence response.
    
    This response provides repository-aware engineering intelligence with
    decisions, evidence, analysis, and actionable recommendations.
    """
    
    # Core question information
    question: str = Field(..., description="The original engineering question")
    intent: str = Field(..., description="The classified intent")
    target_name: str = Field(..., description="The target entity name")
    
    # Engineering Decision
    engineering_decision: EngineeringDecision = Field(..., description="Primary engineering decision")
    
    # Engineering Evidence
    engineering_evidence: EngineeringEvidence = Field(..., description="Repository evidence")
    
    # Repository Analysis
    repository_analysis: RepositoryAnalysis = Field(..., description="Repository structure analysis")
    
    # Affected Components
    affected_components: List[AffectedComponent] = Field(default_factory=list, description="Affected components")
    
    # Risk Assessment
    risk_assessment: RiskAssessment = Field(..., description="Risk assessment")
    
    # Recommended Changes
    recommended_changes: List[RecommendedChange] = Field(default_factory=list, description="Recommended changes")
    
    # Implementation Plan
    implementation_plan: ImplementationPlan = Field(..., description="Implementation plan")
    
    # Testing Checklist
    testing_checklist: TestingChecklist = Field(..., description="Testing checklist")
    
    # Engineering Actions
    engineering_actions: List[EngineeringAction] = Field(default_factory=list, description="Actionable engineering steps")
    
    # Metadata
    grounded_in_repository: bool = Field(..., description="Whether response is grounded in repository data")
    evidence_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall evidence confidence")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    limitations: List[str] = Field(default_factory=list, description="Known limitations in the analysis")
