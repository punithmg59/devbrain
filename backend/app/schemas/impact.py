from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ImpactNode(BaseModel):
    id: str
    name: str
    node_type: str
    file_path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    depth: int
    direction: str
    risk_score: float
    edge_type: str
    inclusion_reason: Optional[str] = None
    risk_tier: Optional[str] = None
    http_method: Optional[str] = None
    route_path: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ImpactFile(BaseModel):
    file_path: str
    file_name: str
    affected_functions: List[str]
    risk_level: str


class AffectedAPI(BaseModel):
    method: str
    path: str
    node_id: str
    name: str
    file_path: str
    inclusion_reason: str


class TestRecommendation(BaseModel):
    title: str
    priority: Literal["critical", "high", "medium"]
    reason: str
    evidence: Optional[str] = None


class DeploymentAdvice(BaseModel):
    summary: str
    recommendations: List[str]
    monitoring: List[str]
    rollback_trigger: Optional[str] = None


class GraphNode(BaseModel):
    id: str
    name: str
    node_type: str
    file_path: str
    risk_tier: str
    is_source: bool = False
    depth: int = 0
    confidence: float = 1.0


class GraphEdge(BaseModel):
    from_id: str
    to_id: str
    edge_type: str
    confidence: float = 1.0


class ImpactGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class ExactDependencyItem(BaseModel):
    id: str
    name: str
    node_type: str
    file_path: str
    confidence: float = 1.0


class ExactDependencies(BaseModel):
    level_1_direct: List[ExactDependencyItem] = Field(default_factory=list)
    level_1_incoming: List[ExactDependencyItem] = Field(default_factory=list)
    level_2_indirect: List[ExactDependencyItem] = Field(default_factory=list)
    level_3_workflow: List[ExactDependencyItem] = Field(default_factory=list)
    database_dependencies: List[ExactDependencyItem] = Field(default_factory=list)
    api_dependencies: List[ExactDependencyItem] = Field(default_factory=list)
    file_dependencies: List[str] = Field(default_factory=list)


class ImpactGraphResponse(BaseModel):
    repo_id: str
    source_node_id: str
    exact_dependencies: ExactDependencies
    graph: ImpactGraph


class ResolvedEntity(BaseModel):
    id: str
    name: str
    node_type: str
    file_path: str
    match_reason: str
    score: float


class BlastRadius(BaseModel):
    functions: int = 0
    classes: int = 0
    api_routes: int = 0
    files: int = 0
    max_depth: int = 0
    total_nodes: int = 0
    verified_edges: int = 0
    scenario: str = "modify"
    workflows_impacted: int = 0
    services_impacted: int = 0
    journeys_impacted: int = 0
    blast_radius_score: int = 0
    risk_category: str = "safe"
    estimated_users_impacted: str = "LOW"
    deployment_risk: str = "low"
    critical_paths_impacted: List[str] = Field(default_factory=list)
    score_breakdown: List[ScoreComponent] = Field(default_factory=list)


class CriticalPathSummary(BaseModel):
    id: str
    name: str
    criticality: str
    description: Optional[str] = None
    impacted_node_names: List[str] = Field(default_factory=list)


class JourneyImpactItem(BaseModel):
    journey_id: str
    journey_name: str
    severity: str
    user_impact: str
    affected_workflows: List[str] = Field(default_factory=list)


class BusinessImpactItem(BaseModel):
    category: str
    impact_label: str
    severity: str
    reason: str
    journey_name: Optional[str] = None


class BlastRadiusReport(BaseModel):
    blast_radius_score: int
    risk_category: str
    functions_impacted: int = 0
    classes_impacted: int = 0
    files_impacted: int = 0
    apis_impacted: int = 0
    workflows_impacted: int = 0
    services_impacted: int = 0
    journeys_impacted: int = 0
    estimated_users_impacted: str = "LOW"
    deployment_risk: str = "low"
    critical_paths_impacted: List[CriticalPathSummary] = Field(default_factory=list)
    service_names: List[str] = Field(default_factory=list)
    journey_names: List[str] = Field(default_factory=list)
    workflow_names: List[str] = Field(default_factory=list)
    score_breakdown: List[ScoreComponent] = Field(default_factory=list)
    summary: str = ""
    journey_impacts: List[JourneyImpactItem] = Field(default_factory=list)
    business_impacts: List[BusinessImpactItem] = Field(default_factory=list)


class BlastRadiusRequest(BaseModel):
    query: str
    max_depth: int = 6
    direction: str = "both"
    scenario: Literal["modify", "delete", "refactor"] = "modify"
    natural_language: bool = True


class ImpactMetricSummary(BaseModel):
    node_id: str
    node_name: Optional[str] = None
    centrality_score: float
    dependency_count: int
    workflow_count: int
    in_degree: int
    out_degree: int


class WorkflowImpact(BaseModel):
    workflow_id: str
    workflow_name: str
    user_impact: str
    evidence_nodes: List[str] = Field(default_factory=list)
    evidence_source: str = "graph_node_match"
    service_name: Optional[str] = None
    severity: str = "medium"
    confidence: float = 0.0
    confidence_percent: float = 0.0
    evidence_chain: Optional[str] = None
    affected_apis: List[str] = Field(default_factory=list)
    recommended_tests: List[str] = Field(default_factory=list)
    criticality: str = "medium"


class PrimaryWorkflow(BaseModel):
    id: str
    name: str
    confidence: float
    confidence_percent: float = 0.0
    service_name: Optional[str] = None


class WorkflowEvidenceItem(BaseModel):
    workflow_id: str
    workflow_name: str
    chain_summary: str
    confidence_percent: float
    steps: List[dict] = Field(default_factory=list)


class ScoreComponent(BaseModel):
    name: str
    points: int
    max_points: int
    evidence: str


class RiskScoreBreakdown(BaseModel):
    total: int
    tier: str
    components: List[ScoreComponent] = Field(default_factory=list)


class ConfidenceBreakdown(BaseModel):
    total: float
    components: List[ScoreComponent] = Field(default_factory=list)


class ChangeRecommendation(BaseModel):
    decision: str
    should_proceed: bool
    label: str


class RolloutStrategy(BaseModel):
    strategy: str
    steps: List[str] = Field(default_factory=list)
    feature_flag_recommended: bool = False
    canary_recommended: bool = False


class RollbackStrategy(BaseModel):
    strategy: str
    steps: List[str] = Field(default_factory=list)
    trigger: Optional[str] = None


class ImpactRequest(BaseModel):
    query: str
    max_depth: int = 6
    direction: str = "both"
    natural_language: bool = True
    scenario: Literal["modify", "delete", "refactor"] = "modify"


class ImpactResult(BaseModel):
    query: str
    resolved_query: str = ""
    resolution_confidence: float = 0.0
    matched_entities: List[ResolvedEntity] = Field(default_factory=list)

    source_node: Optional[dict] = None
    impacted_nodes: List[ImpactNode]
    impacted_files: List[ImpactFile]
    graph: Optional[ImpactGraph] = None
    exact_dependencies: Optional[ExactDependencies] = None

    risk_level: str
    risk_score: float
    risk_score_100: int = 0
    confidence: float = 0.0

    executive_summary: str = ""
    why_this_matters: str = ""
    blast_radius: BlastRadius = Field(default_factory=BlastRadius)

    business_impact: List[str] = Field(default_factory=list)
    engineering_impact: List[str] = Field(default_factory=list)
    developer_impact: List[str] = Field(default_factory=list)
    workflow_impact: List[WorkflowImpact] = Field(default_factory=list)
    primary_workflow: Optional[PrimaryWorkflow] = None
    affected_journeys: List[str] = Field(default_factory=list)
    workflow_evidence: List[WorkflowEvidenceItem] = Field(default_factory=list)
    workflow_confidence: float = 0.0
    user_impact: List[str] = Field(default_factory=list)

    affected_systems: List[str] = Field(default_factory=list)
    affected_apis: List[AffectedAPI] = Field(default_factory=list)

    explanation: str
    risk_analysis: str = ""
    ai_recommendation: str = ""
    staff_engineer_recommendation: str = ""

    recommended_tests: List[TestRecommendation] = Field(default_factory=list)
    deployment_advice: Optional[DeploymentAdvice] = None
    rollout_strategy: RolloutStrategy = Field(default_factory=RolloutStrategy)
    rollback_strategy: RollbackStrategy = Field(default_factory=RollbackStrategy)
    monitoring_plan: List[str] = Field(default_factory=list)

    risk_score_breakdown: RiskScoreBreakdown = Field(
        default_factory=lambda: RiskScoreBreakdown(total=0, tier="safe")
    )
    confidence_breakdown: ConfidenceBreakdown = Field(
        default_factory=lambda: ConfidenceBreakdown(total=0, components=[])
    )
    change_recommendation: ChangeRecommendation = Field(
        default_factory=lambda: ChangeRecommendation(
            decision="requires_review",
            should_proceed=False,
            label="",
        )
    )

    pr_checklist: List[str] = Field(default_factory=list)
    qa_checklist: List[str] = Field(default_factory=list)
    rollback_plan: List[str] = Field(default_factory=list)

    total_affected_functions: int
    total_affected_files: int
    analysis_time_ms: int
    warning: Optional[str] = None
    scenario: str = "modify"
    blast_radius_report: Optional[BlastRadiusReport] = None
    journey_impact_items: List[JourneyImpactItem] = Field(default_factory=list)
    business_impact_items: List[BusinessImpactItem] = Field(default_factory=list)
    version: str = "5.0"
