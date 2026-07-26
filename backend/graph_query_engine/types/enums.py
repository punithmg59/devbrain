"""
Domain enumerations for the Graph Query Engine.

Provides strongly-typed enumerations for traversal directions, entity relationships,
and dependency classifications.
"""

from enum import Enum, StrEnum


class TraversalDirection(StrEnum):
    """
    Direction of edge traversal within a graph query.
    """
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"
    BOTH = "BOTH"


class RelationshipType(StrEnum):
    """
    Core relationship types connecting graph nodes.
    """
    CALLS = "CALLS"
    INHERITS = "INHERITS"
    IMPORTS = "IMPORTS"
    USES = "USES"
    CONTAINS = "CONTAINS"
    DEPENDS_ON = "DEPENDS_ON"
    OVERRIDES = "OVERRIDES"
    IMPLEMENTS = "IMPLEMENTS"
    DEFINES = "DEFINES"
    REFERENCES = "REFERENCES"


class DependencyType(StrEnum):
    """
    Classification of dependencies between components or packages.
    """
    DIRECT = "DIRECT"
    INDIRECT = "INDIRECT"
    TRANSITIVE = "TRANSITIVE"
    DEV = "DEV"
    RUNTIME = "RUNTIME"
    PEER = "PEER"
    OPTIONAL = "OPTIONAL"
