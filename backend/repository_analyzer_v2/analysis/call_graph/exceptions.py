"""
analysis/call_graph/exceptions.py
----------------------------------
Phase 4.8.1, 4.8.2, 4.8.3 — Call Graph Exception Hierarchy.

Defines custom exception classes for call graph construction errors,
indexing errors, and validator execution failures.
"""

from __future__ import annotations


# ----------------------------------------------------------------------
# Phase 4.8.1 Construction Exceptions
# ----------------------------------------------------------------------

class CallGraphBuildError(Exception):
    """Base exception for call graph construction errors."""
    pass


class InvalidNodeError(CallGraphBuildError):
    """Raised when a graph node has invalid or missing required attributes."""
    pass


class InvalidEdgeError(CallGraphBuildError):
    """Raised when a graph edge connects non-existent nodes or has invalid endpoints."""
    pass


class DuplicateNodeError(CallGraphBuildError):
    """Raised or recorded when a node with an existing SymbolId is illegally redefined."""
    pass


class DuplicateEdgeWarning(Warning):
    """Warning emitted when an identical directed edge is encountered and merged via weight increment."""
    pass


# ----------------------------------------------------------------------
# Phase 4.8.2 Index & Query Exceptions
# ----------------------------------------------------------------------

class GraphIndexError(Exception):
    """Base exception for call graph indexing and query engine errors."""
    pass


class InvalidIndexError(GraphIndexError):
    """Raised when a graph index table has corrupted or missing required keys."""
    pass


class MissingNodeError(GraphIndexError):
    """Raised when querying a node symbol_id or FQN that does not exist in the index."""
    pass


class MissingEdgeError(GraphIndexError):
    """Raised when querying an edge caller/callee pair that does not exist in the index."""
    pass


class DuplicateIndexWarning(Warning):
    """Warning emitted when duplicate keys are encountered during index construction."""
    pass


# ----------------------------------------------------------------------
# Phase 4.8.3 Validation Framework Exceptions
# ----------------------------------------------------------------------

class ValidationError(Exception):
    """Base exception raised when the GraphValidator engine encounters an internal execution failure."""
    pass


class NodeValidationError(ValidationError):
    """Raised when the node validation rule fails internally during execution."""
    pass


class EdgeValidationError(ValidationError):
    """Raised when the edge validation rule fails internally during execution."""
    pass


class IntegrityValidationError(ValidationError):
    """Raised when the structural or reference integrity rules fail internally during execution."""
    pass


class IndexValidationError(ValidationError):
    """Raised when the index validation rule fails internally during execution."""
    pass


class GraphConsistencyError(ValidationError):
    """Raised when the graph consistency rule fails internally during execution."""
    pass
