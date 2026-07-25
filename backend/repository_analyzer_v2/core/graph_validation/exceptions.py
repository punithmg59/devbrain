"""
core/graph_validation/exceptions.py
------------------------------------
Domain exceptions for Dependency Graph Validation Framework.
"""


class GraphValidationError(Exception):
    """Base exception for all graph validation errors."""
    pass


class ValidationReportError(GraphValidationError):
    """Raised when validation report construction or processing fails."""
    pass


class ValidationSerializationError(GraphValidationError):
    """Raised when validation report serialization or deserialization fails."""
    pass
