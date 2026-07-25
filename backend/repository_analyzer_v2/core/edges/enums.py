"""
core/edges/enums.py
-------------------
Core Enumerations for DevBrain Relationship Edges.
"""

from enum import Enum


class EdgeKind(str, Enum):
    """
    Canonical Relationship Kind classifications.
    Supports all minimum required relationship kinds across languages and frameworks.
    """
    IMPORT = "import"
    CALL = "call"
    INHERITANCE = "inheritance"
    IMPLEMENTATION = "implementation"
    OVERRIDE = "override"
    REFERENCE = "reference"
    TYPE_REFERENCE = "type_reference"
    RETURN_TYPE = "return_type"
    PARAMETER_TYPE = "parameter_type"
    FIELD_TYPE = "field_type"
    THROWS = "throws"
    DECORATOR = "decorator"
    ANNOTATION = "annotation"
    COMPOSITION = "composition"
    AGGREGATION = "aggregation"
    CONTAINMENT = "containment"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    FRAMEWORK = "framework"
    PLUGIN = "plugin"
    GENERATED = "generated"
    FUTURE = "future"
    UNKNOWN = "unknown"


class EdgeDirection(str, Enum):
    """Directionality of relationship edges."""
    DIRECTED = "directed"
    UNDIRECTED = "undirected"
    BIDIRECTIONAL = "bidirectional"


class EdgeStrength(str, Enum):
    """Semantic coupling strength of relationship edges."""
    STRONG = "strong"
    NORMAL = "normal"
    WEAK = "weak"
    OPTIONAL = "optional"
    GENERATED = "generated"
