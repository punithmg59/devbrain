"""
Public Query API Exceptions.

Hierarchy of exceptions raised by the Public Query API facade.
"""

from typing import Any, Dict, Optional
from graph_query_engine.api.errors import QueryErrorCode, QueryErrorDetail
from graph_query_engine.errors.exceptions import GraphQueryEngineError


class PublicQueryApiException(GraphQueryEngineError):
    """Base exception for all Public Query API errors."""

    def __init__(
        self,
        message: str,
        code: QueryErrorCode = QueryErrorCode.UNKNOWN_ERROR,
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message=message, code=code.value, details=details, cause=cause)
        self.error_detail = QueryErrorDetail(
            code=code,
            message=message,
            target=target,
            details=details or {},
        )


class QueryValidationException(PublicQueryApiException):
    """Raised when request structure or query parameters fail validation."""

    def __init__(
        self,
        message: str,
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=QueryErrorCode.VALIDATION_FAILED,
            target=target,
            details=details,
        )


class QueryExecutionException(PublicQueryApiException):
    """Raised when internal planning or graph traversal execution fails."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=QueryErrorCode.EXECUTION_FAILED,
            details=details,
            cause=cause,
        )


class QueryTimeoutException(PublicQueryApiException):
    """Raised when query execution exceeds specified context timeout limits."""

    def __init__(self, message: str, timeout_seconds: float) -> None:
        super().__init__(
            message=message,
            code=QueryErrorCode.TIMEOUT,
            details={"timeout_seconds": timeout_seconds},
        )


class QueryNotFoundException(PublicQueryApiException):
    """Raised when a requested node, file, or symbol is not found."""

    def __init__(self, message: str, target: Optional[str] = None) -> None:
        super().__init__(
            message=message,
            code=QueryErrorCode.NODE_NOT_FOUND,
            target=target,
        )


class SessionNotFoundException(PublicQueryApiException):
    """Raised when a requested QuerySession ID is invalid or expired."""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            message=f"QuerySession '{session_id}' not found or expired",
            code=QueryErrorCode.SESSION_NOT_FOUND,
            target=session_id,
        )


__all__ = [
    "PublicQueryApiException",
    "QueryValidationException",
    "QueryExecutionException",
    "QueryTimeoutException",
    "QueryNotFoundException",
    "SessionNotFoundException",
]
