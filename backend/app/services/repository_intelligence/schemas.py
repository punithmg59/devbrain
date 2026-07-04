"""
Repository Intelligence Engine Schemas

Strongly typed Pydantic models for the Engineering Evidence Retrieval Engine.
No English summaries. No LLM output. Only structured engineering data.
"""

from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EvidenceCategory(str, Enum):
    """Categories of engineering evidence."""

    CALLER = "caller"
    CALLEE = "callee"
    DEPENDENCY = "dependency"
    DEPENDENT = "dependent"
    IMPORT = "import"
    API = "api"
    DATABASE = "database"
    TEST = "test"
    CRITICAL_PATH = "critical_path"
    CONFIGURATION = "configuration"
    ARCHITECTURE = "architecture"
    INTEGRATION_POINT = "integration_point"
    PATTERN = "pattern"
    SERVICE = "service"
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    MODULE = "module"
    WORKFLOW = "workflow"
    REFERENCE = "reference"


# ---------------------------------------------------------------------------
# Evidence Items
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    """A single piece of structured engineering evidence."""

    model_config = ConfigDict(from_attributes=True)

    node_id: UUID
    name: str
    node_type: str
    full_path: str
    category: EvidenceCategory

    # Code location
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    signature: Optional[str] = None
    raw_code: Optional[str] = None

    # Graph metadata
    architecture_role: Optional[str] = None
    complexity_score: float = 0.0
    is_exported: bool = False
    is_async: bool = False

    # Scoring
    relevance_score: float = Field(0.0, ge=0.0, le=1.0)
    graph_distance: int = Field(0, ge=0, description="Hops from the target node")


class EdgeEvidenceItem(BaseModel):
    """Evidence for a graph relationship."""

    model_config = ConfigDict(from_attributes=True)

    edge_id: UUID
    from_node_id: UUID
    from_node_name: str
    to_node_id: UUID
    to_node_name: str
    edge_type: str
    weight: float = 1.0
    relevance_score: float = Field(0.0, ge=0.0, le=1.0)


class WorkflowEvidenceItem(BaseModel):
    """Evidence for a workflow."""

    model_config = ConfigDict(from_attributes=True)

    workflow_id: UUID
    name: str
    workflow_type: str
    criticality: str
    confidence: float = 0.0
    relevance_score: float = Field(0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Evidence Collection
# ---------------------------------------------------------------------------

class EvidenceCollection(BaseModel):
    """Categorised container for all evidence items."""

    items: Dict[str, List[EvidenceItem]] = Field(
        default_factory=dict,
        description="Evidence items grouped by EvidenceCategory value",
    )
    edges: List[EdgeEvidenceItem] = Field(default_factory=list)
    workflows: List[WorkflowEvidenceItem] = Field(default_factory=list)

    # Convenience accessors
    @property
    def total_items(self) -> int:
        return sum(len(v) for v in self.items.values())

    @property
    def categories_populated(self) -> List[str]:
        return [k for k, v in self.items.items() if v]

    def add(self, category: EvidenceCategory, item: EvidenceItem) -> None:
        """Add an evidence item to the specified category."""
        key = category.value
        if key not in self.items:
            self.items[key] = []
        self.items[key].append(item)

    def get(self, category: EvidenceCategory) -> List[EvidenceItem]:
        """Get all evidence items for a category."""
        return self.items.get(category.value, [])

    def add_edge(self, edge: EdgeEvidenceItem) -> None:
        self.edges.append(edge)

    def add_workflow(self, workflow: WorkflowEvidenceItem) -> None:
        self.workflows.append(workflow)


# ---------------------------------------------------------------------------
# Metadata & Scoring
# ---------------------------------------------------------------------------

class EvidenceMetadata(BaseModel):
    """Statistics about the evidence collection process."""

    total_nodes_scanned: int = 0
    total_edges_traversed: int = 0
    total_items_collected: int = 0
    categories_populated: int = 0
    collection_time_ms: float = 0.0
    collection_methods: List[str] = Field(default_factory=list)


class EvidenceScore(BaseModel):
    """Aggregate quality score for an evidence collection."""

    overall_confidence: float = Field(0.0, ge=0.0, le=1.0)
    coverage_score: float = Field(0.0, ge=0.0, le=1.0)
    density_score: float = Field(0.0, ge=0.0, le=1.0)
    relevance_score: float = Field(0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Top-Level Output
# ---------------------------------------------------------------------------

class EngineeringEvidence(BaseModel):
    """
    Top-level output of the Repository Intelligence Engine.

    This is the structured engineering evidence object returned for every
    intent. Downstream engines consume this — never raw English text.
    """

    model_config = ConfigDict(use_enum_values=True)

    # Intent echo
    intent_type: str
    target_name: str
    target_type: str
    repo_id: UUID

    # Evidence payload
    evidence: EvidenceCollection
    score: EvidenceScore
    metadata: EvidenceMetadata

    # Convenience flags
    has_callers: bool = False
    has_callees: bool = False
    has_tests: bool = False
    has_apis: bool = False
    has_database: bool = False
    has_workflows: bool = False
    has_critical_paths: bool = False
