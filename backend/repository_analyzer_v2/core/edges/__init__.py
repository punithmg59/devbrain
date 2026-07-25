"""
core/edges Package
------------------
Primary Edge Domain Model and EdgeCollection for DevBrain.
"""

from core.edges.diagnostics import (
    EdgeDiagnostic,
    EdgeDiagnostics,
)
from core.edges.enums import (
    EdgeDirection,
    EdgeKind,
    EdgeStrength,
)
from core.edges.evidence import (
    EdgeEvidence,
    EdgeOrigin,
    EdgeVersion,
)
from core.edges.exceptions import (
    EdgeError,
    EdgeIDError,
    EdgeSerializationError,
    EdgeValidationError,
)
from core.edges.ids import EdgeID, generate_edge_id
from core.edges.interfaces import (
    IEdge,
    IEdgeCollection,
)
from core.edges.metadata import (
    EdgeAttributes,
    EdgeMetadata,
)
from core.edges.models import (
    Edge,
    EdgeCollection,
    EdgeStatistics,
)
from core.edges.serialization import (
    EDGE_COLLECTION_VERSION,
    dict_to_edge_collection,
    edge_collection_to_dict,
    edge_collection_to_json,
    hash_edge_collection,
    json_to_edge_collection,
)
from core.edges.validator import EdgeValidator

__all__ = [
    # Models & Enums
    "Edge",
    "EdgeCollection",
    "EdgeStatistics",
    "EdgeKind",
    "EdgeDirection",
    "EdgeStrength",
    # EdgeID Strategy
    "EdgeID",
    "generate_edge_id",
    # Evidence & Metadata
    "EdgeEvidence",
    "EdgeOrigin",
    "EdgeVersion",
    "EdgeMetadata",
    "EdgeAttributes",
    # Diagnostics & Validation
    "EdgeDiagnostic",
    "EdgeDiagnostics",
    "EdgeValidator",
    # Interfaces
    "IEdge",
    "IEdgeCollection",
    # Exceptions
    "EdgeError",
    "EdgeIDError",
    "EdgeValidationError",
    "EdgeSerializationError",
    # Serialization
    "EDGE_COLLECTION_VERSION",
    "edge_collection_to_dict",
    "dict_to_edge_collection",
    "edge_collection_to_json",
    "json_to_edge_collection",
    "hash_edge_collection",
]
