"""Response schemas for Architecture Intelligence V2.

Every value is computed deterministically from graph evidence.
No LLM is ever involved in producing scores, findings, or recommendations.
"""

from pydantic import BaseModel, Field


# ── 1. Critical Component Detector ──────────────────────────────────────


class CriticalComponent(BaseModel):
    node_id: str
    name: str
    node_type: str
    file_path: str | None = None
    influence_score: float = Field(
        ..., ge=0.0, le=100.0,
        description="0–100 influence score based on weighted fan-in, fan-out, "
                    "centrality, and edge weights.",
    )
    fan_in: int
    fan_out: int
    dependents_count: int
    reason: str


class CriticalComponentsResponse(BaseModel):
    repo_id: str
    components: list[CriticalComponent]
    total_nodes: int
    total_edges: int


# ── 2. Bottleneck Detector ──────────────────────────────────────────────


class Bottleneck(BaseModel):
    node_id: str
    name: str
    node_type: str
    file_path: str | None = None
    bottleneck_type: str  # "god_service" | "oversized_module" | "fan_in_explosion" | "fan_out_explosion"
    severity: str  # "critical" | "high" | "medium"
    metric_value: float
    threshold: float
    description: str


class BottlenecksResponse(BaseModel):
    repo_id: str
    bottlenecks: list[Bottleneck]
    total_god_services: int
    total_oversized_modules: int
    total_fan_explosions: int


# ── 3. Refactor Opportunity Engine ──────────────────────────────────────


class CyclicDependency(BaseModel):
    cycle_id: int
    nodes: list[dict]  # [{node_id, name, node_type}]
    length: int
    severity: str  # "critical" | "high" | "medium"


class CouplingPair(BaseModel):
    node_a_id: str
    node_a_name: str
    node_b_id: str
    node_b_name: str
    shared_edges: int
    coupling_score: float
    recommendation: str


class ArchitectureViolation(BaseModel):
    violation_type: str  # "layer_skip" | "circular_dependency" | "bidirectional_coupling"
    description: str
    severity: str
    involved_nodes: list[dict]  # [{node_id, name, node_type}]


class RefactorOpportunitiesResponse(BaseModel):
    repo_id: str
    cyclic_dependencies: list[CyclicDependency]
    tightly_coupled: list[CouplingPair]
    violations: list[ArchitectureViolation]
    total_issues: int


# ── 4. Change Risk Predictor ────────────────────────────────────────────


class ImpactedEntity(BaseModel):
    node_id: str
    name: str
    node_type: str
    file_path: str | None = None
    impact_path_length: int  # hops from the target node


class ChangeRiskReport(BaseModel):
    repo_id: str
    target_node_id: str
    target_node_name: str
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: str  # "critical" | "high" | "medium" | "low"
    impacted_nodes: list[ImpactedEntity]
    impacted_apis: list[ImpactedEntity]
    impacted_services: list[ImpactedEntity]
    impacted_databases: list[ImpactedEntity]
    total_impacted: int
    summary: str


# ── 5. Architecture Findings Generator ──────────────────────────────────


class Finding(BaseModel):
    rank: int
    title: str
    category: str  # "critical_component" | "bottleneck" | "coupling" | "risk" | "health"
    severity: str  # "critical" | "high" | "medium" | "info"
    description: str
    related_node_ids: list[str]
    metric_name: str
    metric_value: float
    recommendation: str


class FindingsResponse(BaseModel):
    repo_id: str
    findings: list[Finding]
    generated_at: str  # ISO timestamp


# ── 6. Intelligence Dashboard (aggregated) ──────────────────────────────


class IntelligenceDashboard(BaseModel):
    repo_id: str
    architecture_score: float = Field(..., ge=0.0, le=100.0)
    risk_score: float = Field(..., ge=0.0, le=100.0)
    architecture_grade: str  # "A" | "B" | "C" | "D" | "F"
    total_nodes: int
    total_edges: int
    critical_components: list[CriticalComponent]
    bottlenecks: list[Bottleneck]
    refactor_suggestions: list[Finding]  # subset of findings related to refactoring
    top_findings: list[Finding]


class ArchitectureIntelligenceResponse(BaseModel):
    """The exact response format requested for the Architecture Intelligence Agent."""
    health_score: float
    risk_score: float
    critical_nodes: list[CriticalComponent]
    bottlenecks: list[Bottleneck]
    single_points_of_failure: list[CriticalComponent]
    refactor_opportunities: list[Finding]
    architecture_findings: list[Finding]

