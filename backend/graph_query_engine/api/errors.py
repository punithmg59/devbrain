"""
Public Query API Error Specifications and Codes.
"""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class QueryErrorCode(str, Enum):
    """Enumeration of Public Query API error codes."""

    UNKNOWN_ERROR = "ERR_UNKNOWN"
    INVALID_REQUEST = "ERR_INVALID_REQUEST"
    VALIDATION_FAILED = "ERR_VALIDATION_FAILED"
    REPOSITORY_NOT_FOUND = "ERR_REPOSITORY_NOT_FOUND"
    NODE_NOT_FOUND = "ERR_NODE_NOT_FOUND"
    SYMBOL_NOT_FOUND = "ERR_SYMBOL_NOT_FOUND"
    PLANNING_FAILED = "ERR_PLANNING_FAILED"
    EXECUTION_FAILED = "ERR_EXECUTION_FAILED"
    TRAVERSAL_FAILED = "ERR_TRAVERSAL_FAILED"
    TIMEOUT = "ERR_TIMEOUT"
    CANCELLED = "ERR_CANCELLED"
    SESSION_NOT_FOUND = "ERR_SESSION_NOT_FOUND"
    UNSUPPORTED_OPERATION = "ERR_UNSUPPORTED_OPERATION"


class QueryErrorDetail(BaseModel):
    """Immutable detailed error descriptor container."""

    model_config = ConfigDict(frozen=True)

    code: QueryErrorCode = Field(default=QueryErrorCode.UNKNOWN_ERROR, description="Categorized error code")
    message: str = Field(..., description="Human-readable error explanation message")
    target: Optional[str] = Field(default=None, description="Target entity or parameter causing error")
    details: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary error diagnostic details")


__all__ = ["QueryErrorCode", "QueryErrorDetail"]
