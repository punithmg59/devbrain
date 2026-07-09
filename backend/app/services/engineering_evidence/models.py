"""Engineering Evidence Engine - Unified Data Models."""

from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

from app.services.reference_intelligence.models import Reference, Criticality


class EvidenceCategory(str, Enum):
    """Category of engineering evidence."""
    RUNTIME = "runtime"
    CONFIGURATION = "configuration"
    INFRASTRUCTURE = "infrastructure"
    DATABASE = "database"
    TESTING = "testing"
    PUBLIC_API = "public_api"
    INTERNAL_SERVICE = "internal_service"
    EXTERNAL_DEPENDENCY = "external_dependency"


class FailureMode(str, Enum):
    """Estimated failure mode if the target is modified."""
    RUNTIME_ERROR = "runtime_error"
    BUILD_ERROR = "build_error"
    CONFIGURATION_ERROR = "configuration_error"
    DEPLOYMENT_ERROR = "deployment_error"
    TEST_FAILURE = "test_failure"
    DATA_CORRUPTION = "data_corruption"
    SERVICE_UNAVAILABLE = "service_unavailable"
    API_FAILURE = "api_failure"
    UNKNOWN = "unknown"


class RiskCategory(str, Enum):
    """Risk category for evidence."""
    DEPLOYMENT = "deployment"
    RUNTIME = "runtime"
    TESTING = "testing"
    CONFIGURATION = "configuration"
    DATABASE = "database"


class RiskAssessment(BaseModel):
    """Risk assessment for a specific category."""
    category: RiskCategory
    risk_level: Criticality
    risk_score: float = Field(ge=0.0, le=1.0, description="Risk score 0-1")
    affected_systems: List[str] = Field(default_factory=list)
    failure_probability: float = Field(ge=0.0, le=1.0, description="Failure probability 0-1")
    description: str


class ASTNode(BaseModel):
    """AST node information from source code analysis."""
    node_type: str = Field(..., description="Type of AST node (e.g., Function, Class, Variable)")
    name: str = Field(..., description="Name of the node")
    file_path: str = Field(..., description="File containing the node")
    line_number: int = Field(..., description="Line number of the node")
    parent: Optional[str] = Field(None, description="Parent node name")
    children: List[str] = Field(default_factory=list, description="Child node names")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DependencyEdge(BaseModel):
    """Edge in the dependency graph."""
    from_node: str = Field(..., description="Source node")
    to_node: str = Field(..., description="Target node")
    edge_type: str = Field(..., description="Type of dependency (e.g., imports, calls, inherits)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    file_path: Optional[str] = Field(None, description="File where dependency was found")


class DependencyGraph(BaseModel):
    """Dependency graph information."""
    nodes: List[str] = Field(default_factory=list, description="All nodes in the graph")
    edges: List[DependencyEdge] = Field(default_factory=list, description="Dependency edges")
    total_nodes: int = 0
    total_edges: int = 0


class CallGraph(BaseModel):
    """Call graph information."""
    function_calls: List[Dict[str, Any]] = Field(default_factory=list, description="Function call relationships")
    call_depth: int = 0
    entry_points: List[str] = Field(default_factory=list, description="Entry point functions")


class ClassInfo(BaseModel):
    """Information about a class in the repository."""
    name: str = Field(..., description="Class name")
    file_path: str = Field(..., description="File containing the class")
    line_number: int = Field(..., description="Line number of class definition")
    methods: List[str] = Field(default_factory=list, description="Method names")
    attributes: List[str] = Field(default_factory=list, description="Attribute names")
    base_classes: List[str] = Field(default_factory=list, description="Inherited classes")
    derived_classes: List[str] = Field(default_factory=list, description="Classes inheriting from this class")


class FunctionInfo(BaseModel):
    """Information about a function in the repository."""
    name: str = Field(..., description="Function name")
    file_path: str = Field(..., description="File containing the function")
    line_number: int = Field(..., description="Line number of function definition")
    parameters: List[str] = Field(default_factory=list, description="Parameter names")
    return_type: Optional[str] = Field(None, description="Return type")
    calls: List[str] = Field(default_factory=list, description="Functions called by this function")
    called_by: List[str] = Field(default_factory=list, description="Functions that call this function")


class APIRoute(BaseModel):
    """Information about an API route."""
    path: str = Field(..., description="Route path")
    method: str = Field(..., description="HTTP method")
    handler: str = Field(..., description="Handler function name")
    file_path: str = Field(..., description="File containing the route")
    line_number: int = Field(..., description="Line number of route definition")
    middleware: List[str] = Field(default_factory=list, description="Middleware applied")


class ImportInfo(BaseModel):
    """Information about an import statement."""
    module: str = Field(..., description="Imported module")
    alias: Optional[str] = Field(None, description="Import alias")
    file_path: str = Field(..., description="File containing the import")
    line_number: int = Field(..., description="Line number of import")
    import_type: str = Field(..., description="Type of import (e.g., from_import, direct_import)")


class EvidenceGroup(BaseModel):
    """A group of references with calculated metrics."""
    category: EvidenceCategory
    references: List[Reference] = Field(default_factory=list)
    
    # Calculated metrics
    criticality: Criticality
    impact_score: float = Field(ge=0.0, le=1.0, description="Impact score 0-1")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    
    # Engineering summary
    engineering_summary: str
    highest_risk_references: List[Reference] = Field(default_factory=list)
    estimated_failure_mode: FailureMode
    risk_drivers: List[str] = Field(default_factory=list)
    affected_systems: List[str] = Field(default_factory=list)
    
    # Additional metrics
    reference_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    
    def calculate_metrics(self) -> None:
        """Calculate metrics from references."""
        self.reference_count = len(self.references)
        
        for ref in self.references:
            if ref.criticality == Criticality.CRITICAL:
                self.critical_count += 1
            elif ref.criticality == Criticality.HIGH:
                self.high_count += 1
            elif ref.criticality == Criticality.MEDIUM:
                self.medium_count += 1
            elif ref.criticality == Criticality.LOW:
                self.low_count += 1
        
        # Sort references by criticality for highest risk
        self.references.sort(
            key=lambda r: (
                0 if r.criticality == Criticality.CRITICAL else
                1 if r.criticality == Criticality.HIGH else
                2 if r.criticality == Criticality.MEDIUM else
                3
            )
        )
        self.highest_risk_references = self.references[:5]  # Top 5 highest risk


class EngineeringEvidence(BaseModel):
    """Structured engineering evidence derived from raw references.
    
    This is the single source of truth for engineering decisions.
    Consumed by Reasoning Engine, Simulation Engine, and Engineering Report.
    
    All AI responses must be grounded in this repository evidence.
    """
    target_id: UUID
    target_name: str
    target_type: str
    repo_id: UUID
    
    # Evidence groups
    runtime: Optional[EvidenceGroup] = None
    configuration: Optional[EvidenceGroup] = None
    infrastructure: Optional[EvidenceGroup] = None
    database: Optional[EvidenceGroup] = None
    testing: Optional[EvidenceGroup] = None
    public_api: Optional[EvidenceGroup] = None
    internal_service: Optional[EvidenceGroup] = None
    external_dependency: Optional[EvidenceGroup] = None
    
    # Repository structure data (AST, dependency graph, call graph)
    ast_nodes: List[ASTNode] = Field(default_factory=list, description="AST nodes from source code")
    dependency_graph: Optional[DependencyGraph] = Field(None, description="Dependency graph")
    call_graph: Optional[CallGraph] = Field(None, description="Call graph")
    
    # Repository entities
    classes: List[ClassInfo] = Field(default_factory=list, description="Classes in repository")
    functions: List[FunctionInfo] = Field(default_factory=list, description="Functions in repository")
    api_routes: List[APIRoute] = Field(default_factory=list, description="API routes")
    imports: List[ImportInfo] = Field(default_factory=list, description="Import statements")
    
    # Overall metrics
    total_references: int = 0
    overall_criticality: Criticality = Criticality.LOW
    overall_impact_score: float = 0.0
    overall_confidence: float = 0.0
    
    # Executive summary
    overall_summary: str
    
    # Risk assessments by category
    deployment_risk: Optional[RiskAssessment] = None
    runtime_risk: Optional[RiskAssessment] = None
    testing_risk: Optional[RiskAssessment] = None
    configuration_risk: Optional[RiskAssessment] = None
    database_risk: Optional[RiskAssessment] = None
    
    # Critical findings
    critical_findings: List[str] = Field(default_factory=list)
    
    # Affected systems
    affected_systems: List[str] = Field(default_factory=list)
    
    # Recommended validation steps
    recommended_validation_steps: List[str] = Field(default_factory=list)
    
    # Evidence confidence
    evidence_confidence: float = Field(ge=0.0, le=1.0, description="Overall evidence confidence 0-1")
    
    # Data completeness and limitations
    data_completeness: Dict[str, float] = Field(default_factory=dict, description="Completeness score for each data type 0-1")
    limitations: List[str] = Field(default_factory=list, description="Known limitations in the evidence")
    missing_data_types: List[str] = Field(default_factory=list, description="Data types that could not be collected")
    
    def calculate_overall_metrics(self) -> None:
        """Calculate overall metrics from evidence groups."""
        groups = [
            self.runtime,
            self.configuration,
            self.infrastructure,
            self.database,
            self.testing,
            self.public_api,
            self.internal_service,
            self.external_dependency,
        ]
        
        # Count total references
        self.total_references = sum(
            group.reference_count for group in groups if group
        )
        
        # Calculate overall criticality
        critical_count = sum(
            group.critical_count for group in groups if group
        )
        high_count = sum(
            group.high_count for group in groups if group
        )
        
        if critical_count > 0:
            self.overall_criticality = Criticality.CRITICAL
        elif high_count > 0:
            self.overall_criticality = Criticality.HIGH
        elif self.total_references > 10:
            self.overall_criticality = Criticality.MEDIUM
        else:
            self.overall_criticality = Criticality.LOW
        
        # Calculate overall impact score
        impact_scores = [
            group.impact_score for group in groups if group
        ]
        if impact_scores:
            self.overall_impact_score = sum(impact_scores) / len(impact_scores)
        
        # Calculate overall confidence
        confidence_scores = [
            group.confidence for group in groups if group
        ]
        if confidence_scores:
            self.overall_confidence = sum(confidence_scores) / len(confidence_scores)
        
        # Collect affected systems from all groups
        self.affected_systems = []
        for group in groups:
            if group:
                self.affected_systems.extend(group.affected_systems)
        self.affected_systems = list(set(self.affected_systems))  # Deduplicate
        
        # Calculate evidence confidence based on data quality
        self.evidence_confidence = self._calculate_evidence_confidence(groups)
    
    def _calculate_evidence_confidence(self, groups: List[Optional[EvidenceGroup]]) -> float:
        """Calculate overall evidence confidence."""
        if not groups:
            return 0.0
        
        non_empty_groups = [g for g in groups if g and g.reference_count > 0]
        if not non_empty_groups:
            return 0.0
        
        # Base confidence from group confidences
        group_confidences = [g.confidence for g in non_empty_groups]
        avg_confidence = sum(group_confidences) / len(group_confidences)
        
        # Boost based on coverage (more groups = higher confidence)
        coverage_boost = min(len(non_empty_groups) / 8.0, 0.2)
        
        # Boost based on total reference count
        count_boost = min(self.total_references / 100.0, 0.1)
        
        final_confidence = avg_confidence + coverage_boost + count_boost
        return min(final_confidence, 1.0)
    
    def calculate_data_completeness(self) -> None:
        """Calculate completeness scores for each data type."""
        completeness = {}
        
        # AST nodes completeness
        completeness['ast_nodes'] = min(len(self.ast_nodes) / 10.0, 1.0) if self.ast_nodes else 0.0
        
        # Dependency graph completeness
        if self.dependency_graph:
            completeness['dependency_graph'] = min(self.dependency_graph.total_edges / 20.0, 1.0)
        else:
            completeness['dependency_graph'] = 0.0
        
        # Call graph completeness
        if self.call_graph:
            completeness['call_graph'] = min(len(self.call_graph.function_calls) / 10.0, 1.0)
        else:
            completeness['call_graph'] = 0.0
        
        # Classes completeness
        completeness['classes'] = min(len(self.classes) / 5.0, 1.0) if self.classes else 0.0
        
        # Functions completeness
        completeness['functions'] = min(len(self.functions) / 20.0, 1.0) if self.functions else 0.0
        
        # API routes completeness
        completeness['api_routes'] = min(len(self.api_routes) / 5.0, 1.0) if self.api_routes else 0.0
        
        # Imports completeness
        completeness['imports'] = min(len(self.imports) / 10.0, 1.0) if self.imports else 0.0
        
        self.data_completeness = completeness
        
        # Identify missing data types
        self.missing_data_types = [
            data_type for data_type, score in completeness.items() if score == 0.0
        ]
    
    def generate_limitation_statements(self) -> None:
        """Generate limitation statements based on data completeness."""
        self.limitations = []
        
        if self.data_completeness.get('ast_nodes', 0.0) < 0.5:
            self.limitations.append("Limited AST information available - code structure analysis may be incomplete.")
        
        if self.data_completeness.get('dependency_graph', 0.0) < 0.5:
            self.limitations.append("Dependency graph incomplete - some dependencies may not be captured.")
        
        if self.data_completeness.get('call_graph', 0.0) < 0.5:
            self.limitations.append("Call graph incomplete - function call relationships may be missing.")
        
        if self.data_completeness.get('classes', 0.0) < 0.5:
            self.limitations.append("Limited class information available - class hierarchy may be incomplete.")
        
        if self.data_completeness.get('functions', 0.0) < 0.5:
            self.limitations.append("Limited function information available - function signatures may be missing.")
        
        if self.data_completeness.get('api_routes', 0.0) < 0.5:
            self.limitations.append("Limited API route information available - API surface may be incomplete.")
        
        if self.data_completeness.get('imports', 0.0) < 0.5:
            self.limitations.append("Limited import information available - external dependencies may be incomplete.")
        
        if self.evidence_confidence < 0.5:
            self.limitations.append(f"Low overall evidence confidence ({self.evidence_confidence:.2f}) - results should be verified.")
        
        if not self.limitations:
            self.limitations.append("All repository data types collected successfully.")
