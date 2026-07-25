"""
core/namespaces/exceptions.py
------------------------------
Domain exceptions for the Namespace Builder & NamespaceTree.
"""


class NamespaceError(Exception):
    """Base exception for all namespace domain errors."""
    pass


class NamespaceIDError(NamespaceError):
    """Raised when NamespaceID generation or validation fails."""
    pass


class NamespaceValidationError(NamespaceError):
    """Raised when NamespaceNode or NamespaceTree validation fails."""
    pass


class NamespaceTraversalError(NamespaceError):
    """Raised when namespace AST traversal encounters fatal errors."""
    pass


class NamespaceSerializationError(NamespaceError):
    """Raised when NamespaceTree serialization or deserialization fails."""
    pass
