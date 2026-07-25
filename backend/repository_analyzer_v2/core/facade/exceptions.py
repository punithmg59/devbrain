"""
core/facade/exceptions.py
-------------------------
Domain exceptions for DependencyGraph Facade.
"""


class FacadeError(Exception):
    """Base exception for all facade errors."""
    pass


class FacadePipelineError(FacadeError):
    """Raised when an unhandled error occurs during pipeline orchestration."""
    pass


class FacadeSerializationError(FacadeError):
    """Raised when facade result serialization or deserialization fails."""
    pass
