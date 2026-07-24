"""
analysis/call_graph/exceptions.py
----------------------------------
Phase 4.8.1 — Call Graph Exception Hierarchy.

Defines custom exception classes for call graph construction errors,
node/edge validation failures, and duplicate handling.
"""

from __future__ import annotations


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
