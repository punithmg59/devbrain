from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator

class FolderResponse(BaseModel):
    id: str
    repo_id: str
    folder_path: str
    folder_name: str
    parent_path: Optional[str] = None
    depth: int
    file_count: int
    function_count: int
    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "repo_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v: object) -> str:
        return str(v)

class FileResponse(BaseModel):
    id: str
    repo_id: str
    file_path: str
    file_name: str
    extension: Optional[str] = None
    language: Optional[str] = None
    folder_path: str
    depth: int
    size_bytes: int
    line_count: int
    content_preview: Optional[str] = None
    importance_score: float
    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "repo_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v: object) -> str:
        return str(v)

class NodeResponse(BaseModel):
    id: str
    repo_id: str
    file_id: Optional[str] = None
    node_type: str
    name: str
    full_path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    raw_code: Optional[str] = None
    signature: Optional[str] = None
    calls: List[str] = []
    called_by: List[str] = []
    http_method: Optional[str] = None
    route_path: Optional[str] = None
    summary: Optional[str] = None
    detailed_explanation: Optional[str] = None
    architecture_role: Optional[str] = None
    complexity_level: Optional[str] = None
    call_flow_diagram: Optional[str] = None
    ai_tags: List[str] = []
    potential_risks: List[str] = []
    dependencies: List[str] = []
    responsibilities: List[str] = []
    inputs: List[str] = []
    outputs: List[str] = []
    related_components: List[str] = []
    call_flow: List[str] = []
    tags: List[str] = []
    is_exported: bool = False
    is_async: bool = False
    complexity_score: float = 0.0
    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "repo_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v: object) -> str:
        return str(v)

    @field_validator("file_id", mode="before")
    @classmethod
    def file_id_to_str(cls, v: object) -> Optional[str]:
        return str(v) if v is not None else None

class EdgeResponse(BaseModel):
    id: str
    from_node_id: str
    to_node_id: str
    edge_type: str
    weight: float
    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "from_node_id", "to_node_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v: object) -> str:
        return str(v)

class DependencyRisk(BaseModel):
    score: int
    level: str
    reason: str

class NodeRelation(BaseModel):
    edge_id: str
    node_id: str
    name: str
    type: str
    full_path: str
    file_path: Optional[str] = None
    edge_type: str

class NodeDependenciesResponse(BaseModel):
    node: NodeResponse
    calls: List[NodeRelation] = []
    called_by: List[NodeRelation] = []
    api_routes: List[NodeRelation] = []
    reads_tables: List[NodeRelation] = []
    writes_tables: List[NodeRelation] = []
    updates_tables: List[NodeRelation] = []
    deletes_tables: List[NodeRelation] = []
    services: List[NodeRelation] = []
    auth_dependencies: List[NodeRelation] = []
    imports: List[NodeRelation] = []
    inherits: List[NodeRelation] = []
    contains: List[NodeRelation] = []
    dependency_injections: List[NodeRelation] = []
    risk: DependencyRisk

class FileTreeItem(BaseModel):
    id: str
    name: str
    path: str
    type: str  # "file" or "folder"
    depth: int
    children: List['FileTreeItem'] = []
    file_count: Optional[int] = None
    function_count: Optional[int] = None
    extension: Optional[str] = None
    language: Optional[str] = None
    line_count: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def uuid_to_str(cls, v: object) -> str:
        return str(v)

FileTreeItem.model_rebuild()

class PaginatedFiles(BaseModel):
    files: List[FileResponse]
    total: int
    page: int
    limit: int
    has_more: bool
    model_config = ConfigDict(from_attributes=True)

class PaginatedNodes(BaseModel):
    nodes: List[NodeResponse]
    total: int
    page: int
    limit: int
    has_more: bool
    model_config = ConfigDict(from_attributes=True)

class FileWithNodes(BaseModel):
    file: FileResponse
    nodes: List[NodeResponse]
    model_config = ConfigDict(from_attributes=True)

class NodeWithRelations(BaseModel):
    node: NodeResponse
    file: Optional[FileResponse] = None
    calls: List[dict] = []
    called_by: List[dict] = []
    model_config = ConfigDict(from_attributes=True)

class RepoStats(BaseModel):
    node_types: dict
    extensions: dict
    languages: dict
    top_files_by_size: List[FileResponse]
    top_complex_nodes: List[NodeResponse]
    total_edges: int
    total_api_routes: int
    model_config = ConfigDict(from_attributes=True)

class NodeSummaryRequest(BaseModel):
    force: bool = False
    model_config = ConfigDict(from_attributes=True)

class NodeSummaryResponse(BaseModel):
    node_id: str
    summary: str
    detailed_explanation: Optional[str] = None
    architecture_role: Optional[str] = None
    complexity_level: Optional[str] = None
    call_flow_diagram: Optional[str] = None
    ai_tags: List[str] = []
    potential_risks: List[str] = []
    dependencies: List[str] = []
    responsibilities: List[str] = []
    inputs: List[str] = []
    outputs: List[str] = []
    related_components: List[str] = []
    call_flow: List[str] = []
    tags: List[str] = []
    model_config = ConfigDict(from_attributes=True)

# ── Compatibility Aliases and Extra Classes for Router ──
FileTreeNode = FileTreeItem
PaginatedFilesResponse = PaginatedFiles
PaginatedNodesResponse = PaginatedNodes
FileDetailResponse = FileWithNodes
NodeDetailResponse = NodeWithRelations
RepoStatsResponse = RepoStats

class NodeRelation(BaseModel):
    node_id: str
    name: str
    type: str
    file_path: str
    model_config = ConfigDict(from_attributes=True)

class RepoDetailResponse(BaseModel):
    id: str
    full_name: str
    name: str
    description: Optional[str]
    language: Optional[str]
    analysis_status: str
    last_analyzed_at: Optional[datetime]
    total_files: int
    total_functions: int
    total_lines: int
    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def uuid_to_str(cls, v: object) -> str:
        return str(v)

class ApiRoutesResponse(BaseModel):
    routes: List[NodeResponse]
    total: int
    model_config = ConfigDict(from_attributes=True)


# ── Impact Radar V2 ──────────────────────────────────

class ImpactAnalysisRequest(BaseModel):
    query: str
    scenario: str = "delete"  # delete | modify | rename | move
    new_name: Optional[str] = None
    new_file_path: Optional[str] = None

class ImpactEvidence(BaseModel):
    source: str        # e.g. "summarize_all_nodes"
    target: str        # e.g. "_batch_summarize"
    edge_type: str     # e.g. "calls"
    depth: int
    chain: List[str]   # full evidence chain path

class AffectedItemV2(BaseModel):
    name: str
    node_type: str
    file_path: str
    evidence: ImpactEvidence

class BlastRadiusV2(BaseModel):
    direct_dependents: int
    indirect_dependents: int
    api_impact: int
    database_impact: int
    service_impact: int
    file_impact: int
    auth_impact: int
    class_impact: int
    total_nodes_affected: int
    cycles_detected: int

class RiskFactorV2(BaseModel):
    factor: str
    count: int
    weight: int
    contribution: int

class RiskResultV2(BaseModel):
    score: int  # 0-100
    level: str  # Safe | Low | Medium | High | Critical
    scenario: str
    factors: List[RiskFactorV2]

class FuzzyMatch(BaseModel):
    node_id: str
    name: str
    node_type: str
    file_path: str
    score: float

class ImpactReportV2(BaseModel):
    # Metadata
    query: str
    scenario: str
    resolved_node_id: Optional[str] = None
    resolved_node_name: Optional[str] = None
    resolved_node_type: Optional[str] = None
    resolved_file_path: Optional[str] = None
    fuzzy_matches: List[FuzzyMatch] = []

    # Blast Radius
    blast_radius: BlastRadiusV2

    # Risk
    risk: RiskResultV2

    # Affected Items with Evidence
    direct_callers: List[AffectedItemV2] = []
    indirect_callers: List[AffectedItemV2] = []
    affected_apis: List[AffectedItemV2] = []
    affected_tables: List[AffectedItemV2] = []
    affected_services: List[AffectedItemV2] = []
    affected_files: List[str] = []
    affected_classes: List[AffectedItemV2] = []
    affected_auth: List[AffectedItemV2] = []

    # LLM Explanation (graph-first, LLM-second)
    executive_summary: str = ""
    business_impact: List[str] = []
    developer_impact: List[str] = []
    recommended_tests: List[str] = []
    deployment_recommendation: str = ""
    rollback_strategy: str = ""

    # Analysis Metadata
    analysis_time_ms: int = 0
    graph_traversal_depth: int = 5
    evidence_count: int = 0


# ── Project Brain Dashboard ──────────────────────────

class RepoIntelligenceScore(BaseModel):
    total_score: int
    code_health: int
    dependency_health: int
    architecture_health: int
    engineering_quality: int
    risk_exposure: int

class ArchitectureMap(BaseModel):
    frontend_components: int
    backend_services: int
    api_routes: int
    database_tables: int

class DependencyHealth(BaseModel):
    healthy: int
    risky: int
    circular: int
    orphaned: int

class CriticalFunction(BaseModel):
    node_id: str
    name: str
    file_path: str
    importance_score: int
    inbound_calls: int
    api_usage: int
    db_usage: int
    service_usage: int

class ConnectedComponent(BaseModel):
    node_id: str
    name: str
    degree: int

class DatabaseHotspot(BaseModel):
    node_id: str
    name: str
    total_reads: int
    total_writes: int
    total_updates: int
    total_deletes: int
    touching_functions: List[str]

class HighRiskApi(BaseModel):
    node_id: str
    name: str
    route_path: Optional[str] = None
    risk_score: int
    tables_touched: int
    functions_touched: int

class ArchitectureViolation(BaseModel):
    id: str
    severity: str # Critical, High, Medium, Info
    rule_name: str
    description: str
    source_node_id: Optional[str] = None
    target_node_id: Optional[str] = None
    file_path: Optional[str] = None

class ProjectBrainResponse(BaseModel):
    repo_id: str
    intelligence_score: RepoIntelligenceScore
    architecture_map: ArchitectureMap
    dependency_health: DependencyHealth
    critical_functions: List[CriticalFunction]
    connected_components: List[ConnectedComponent]
    database_hotspots: List[DatabaseHotspot]
    high_risk_apis: List[HighRiskApi]
    architecture_violations: List[ArchitectureViolation]

