"""
core/call_edges/exceptions.py
------------------------------
Domain exceptions for Call Edge Builder.
"""


class CallBuilderError(Exception):
    """Base exception for all call edge builder errors."""
    pass


class CallResolutionError(CallBuilderError):
    """Raised when an unhandled error occurs during callee resolution."""
    pass


class CallValidationError(CallBuilderError):
    """Raised when call edge validation fails."""
    pass


class CallSerializationError(CallBuilderError):
    """Raised when call edge serialization or deserialization fails."""
    pass
