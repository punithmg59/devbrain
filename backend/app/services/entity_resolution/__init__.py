"""Entity Resolution layer - Extracts and resolves entities from natural language."""

from .entity_extractor import EntityExtractor
from .entity_resolver import EntityResolver
from .models import (
    EngineeringAction,
    TargetType,
    RepositoryNode,
    EntityExtraction,
    ResolutionResult
)
from .node_resolver import NodeResolver

__all__ = [
    "EntityExtractor",
    "EntityResolver",
    "NodeResolver",
    "EngineeringAction",
    "TargetType",
    "RepositoryNode",
    "EntityExtraction",
    "ResolutionResult"
]
