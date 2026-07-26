"""
Base Error class for Graph Query Engine.
"""

from datetime import datetime, timezone
import traceback
from typing import Any, Optional

from graph_query_engine.errors.codes import ErrorCode


class GraphQueryError(Exception):
    """
    Root exception for all Graph Query Engine errors.

    Supports structured error context including unique error codes, human readable messages,
    metadata dictionaries, explicit exception chaining (cause), UTC timestamping,
    and captured stack traces.
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode | str = ErrorCode.GENERIC_ERROR,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.code: ErrorCode | str = code
        self.metadata: dict[str, Any] = metadata if metadata is not None else {}
        self.cause: Optional[BaseException] = cause
        self.timestamp: datetime = timestamp or datetime.now(timezone.utc)
        
        if cause is not None and self.__cause__ is None:
            self.__cause__ = cause

        if stack_trace is not None:
            self.stack_trace: str = stack_trace
        else:
            self.stack_trace: str = "".join(traceback.format_stack())

    def to_dict(self) -> dict[str, Any]:
        """
        Serializes error context into a plain dictionary representation.
        """
        return {
            "code": str(self.code),
            "message": self.message,
            "metadata": self.metadata,
            "cause": str(self.cause) if self.cause else None,
            "timestamp": self.timestamp.isoformat(),
            "stack_trace": self.stack_trace,
        }

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"code={self.code!r}, "
            f"message={self.message!r}, "
            f"metadata={self.metadata!r}, "
            f"cause={self.cause!r})"
        )
