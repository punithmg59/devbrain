"""
Traversal Request Representation Models.

Pure structural representation of traversal queries without graph execution logic.
"""

from enum import StrEnum
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.query.predicates import QueryPredicate
from graph_query_engine.types import RelationshipType


class TraversalDirection(StrEnum):
    """Traversal direction constraint enum."""
    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"
    BOTH = "BOTH"
    UNDIRECTED = "UNDIRECTED"


class TraversalConstraint(BaseModel):
    """
    Immutable depth and entity bounds for traversal operations.
    """
    model_config = ConfigDict(frozen=True)

    min_depth: int = Field(default=1, ge=0, description="Minimum traversal depth constraint")
    max_depth: int = Field(default=1, ge=0, description="Maximum traversal depth constraint")
    relationship_types: Tuple[RelationshipType, ...] = Field(default_factory=tuple, description="Filter tuple of allowed relationship types")
    node_types: Tuple[str, ...] = Field(default_factory=tuple, description="Filter tuple of target node type strings")


class TerminationCondition(BaseModel):
    """
    Immutable termination condition evaluating when to stop graph traversal.
    """
    model_config = ConfigDict(frozen=True)

    max_nodes: Optional[int] = Field(default=None, gt=0, description="Stop traversal after visiting max_nodes")
    target_node_types: Tuple[str, ...] = Field(default_factory=tuple, description="Stop traversal when reaching target node types")
    stop_predicate: Optional[QueryPredicate] = Field(default=None, description="Stop traversal if predicate evaluates true")


class TraversalOptions(BaseModel):
    """
    Immutable algorithm preferences and flags for graph traversal.
    """
    model_config = ConfigDict(frozen=True)

    breadth_first: bool = Field(default=True, description="Prefer BFS over DFS if True")
    detect_cycles: bool = Field(default=True, description="Enable cycle detection and prevention")
    track_paths: bool = Field(default=False, description="Track complete node/edge path histories")
    max_memory_bytes: Optional[int] = Field(default=None, description="Memory limit override for traversal state")


class TraversalRequest(BaseModel):
    """
    Declarative representation of a graph traversal request.
    Does NOT perform any graph traversal or execution.
    """
    model_config = ConfigDict(frozen=True)

    direction: TraversalDirection = Field(default=TraversalDirection.OUTGOING, description="Traversal direction")
    constraints: TraversalConstraint = Field(default_factory=TraversalConstraint, description="Depth and type constraints")
    termination: TerminationCondition = Field(default_factory=TerminationCondition, description="Termination rules")
    options: TraversalOptions = Field(default_factory=TraversalOptions, description="Traversal preferences")
    filter_predicate: Optional[QueryPredicate] = Field(default=None, description="Optional node/edge filter predicate")


__all__ = [
    "TraversalDirection",
    "TraversalConstraint",
    "TerminationCondition",
    "TraversalOptions",
    "TraversalRequest",
]
