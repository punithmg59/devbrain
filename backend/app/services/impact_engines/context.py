from dataclasses import dataclass, field
from typing import Any, Literal

Scenario = Literal["modify", "delete", "refactor"]


@dataclass
class ImpactContext:
    """Shared state passed through all deterministic engines."""

    query: str
    repo_id: str
    repo_name: str
    max_depth: int
    direction: str
    scenario: Scenario
    natural_language: bool

    source_node: dict | None = None
    matched_entities: list[dict] = field(default_factory=list)
    resolution_confidence: float = 0.0

    impacted_nodes: list[dict] = field(default_factory=list)
    graph_edges: list[dict] = field(default_factory=list)
    centrality: dict[str, float] = field(default_factory=dict)
    exact_dependencies: dict[str, Any] = field(default_factory=dict)
    traversal_warning: str | None = None

    apis: list[dict] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    affected_services: list[str] = field(default_factory=list)
    files_grouped: list[dict] = field(default_factory=list)

    risk_score_100: int = 0
    risk_level: str = "low"
    risk_breakdown: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    confidence_breakdown: dict[str, Any] = field(default_factory=dict)

    blast_radius: dict[str, Any] = field(default_factory=dict)
    blast_radius_report: dict[str, Any] = field(default_factory=dict)
    critical_paths_impacted: list[dict] = field(default_factory=list)
    journey_impacts: list[dict] = field(default_factory=list)
    business_impacts_structured: list[dict] = field(default_factory=list)
    workflow_impact: list[dict] = field(default_factory=list)
    primary_workflow: dict | None = None
    affected_journeys: list[str] = field(default_factory=list)
    workflow_evidence: list[dict] = field(default_factory=list)
    workflow_confidence: float = 0.0
    workflow_graph_chain: list[tuple[str, str]] = field(default_factory=list)
    user_impact: list[str] = field(default_factory=list)
    business_impact: list[str] = field(default_factory=list)
    engineering_impact: list[str] = field(default_factory=list)

    recommended_tests: list[dict] = field(default_factory=list)
    rollout_strategy: dict[str, Any] = field(default_factory=dict)
    rollback_strategy: dict[str, Any] = field(default_factory=dict)
    monitoring_plan: list[str] = field(default_factory=list)

    change_recommendation: str = "requires_review"
    should_proceed: bool = False
    proceed_label: str = ""

    # LLM-filled (narrative only)
    executive_summary: str = ""
    why_this_matters: str = ""
    staff_engineer_recommendation: str = ""

    analysis_time_ms: int = 0
