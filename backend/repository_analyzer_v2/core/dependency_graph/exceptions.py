"""
core/dependency_graph/exceptions.py
------------------------------------
Domain exceptions for Dependency Graph Builder.
"""


class GraphBuilderError(Exception):
    """Base exception for all dependency graph builder errors."""
    pass


class GraphValidationError(GraphBuilderError):
    """Raised when dependency graph integrity validation fails."""
    pass


class GraphSerializationError(GraphBuilderError):
    """Raised when dependency graph serialization or deserialization fails."""
    pass
