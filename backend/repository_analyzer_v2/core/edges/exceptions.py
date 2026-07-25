"""
core/edges/exceptions.py
-------------------------
Domain exceptions for Primary Edge Domain Model & EdgeCollection.
"""


class EdgeError(Exception):
    """Base exception for all edge domain errors."""
    pass


class EdgeIDError(EdgeError):
    """Raised when an invalid EdgeID is constructed or generated."""
    pass


class EdgeValidationError(EdgeError):
    """Raised when Edge structural validation fails."""
    pass


class EdgeSerializationError(EdgeError):
    """Raised when Edge or EdgeCollection serialization fails."""
    pass
