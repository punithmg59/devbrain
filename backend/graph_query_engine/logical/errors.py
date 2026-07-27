"""
Logical Planner Specific Exception Hierarchy.
"""

from typing import Any, Dict, Optional
from graph_query_engine.errors import ErrorCode, PlannerError


class UnknownOperatorError(PlannerError):
    """Raised when an unrecognized or unhandled AST operator is encountered during lowering."""

    def __init__(
        self,
        message: str,
        stage: str = "ASTLowering",
        operator: Optional[str] = None,
        node_ref: Optional[str] = None,
        diagnostic_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = {
            "stage": stage,
            "operator": operator,
            "node_ref": node_ref,
            "diagnostic_info": diagnostic_info or {},
        }
        super().__init__(message, details=details)
        self.code = ErrorCode.PLANNER_ERROR
        self.stage = stage
        self.operator = operator
        self.node_ref = node_ref
        self.diagnostic_info = diagnostic_info or {}


class LoweringError(PlannerError):
    """Raised when AST → Logical Plan lowering transformation fails."""

    def __init__(
        self,
        message: str,
        stage: str = "ASTLowering",
        operator: Optional[str] = None,
        node_ref: Optional[str] = None,
        diagnostic_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = {
            "stage": stage,
            "operator": operator,
            "node_ref": node_ref,
            "diagnostic_info": diagnostic_info or {},
        }
        super().__init__(message, details=details)
        self.code = ErrorCode.PLANNER_ERROR
        self.stage = stage
        self.operator = operator
        self.node_ref = node_ref
        self.diagnostic_info = diagnostic_info or {}


class LogicalValidationError(PlannerError):
    """Raised when structural validation of a LogicalPlan fails."""

    def __init__(
        self,
        message: str,
        stage: str = "LogicalValidation",
        operator: Optional[str] = None,
        node_ref: Optional[str] = None,
        diagnostic_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = {
            "stage": stage,
            "operator": operator,
            "node_ref": node_ref,
            "diagnostic_info": diagnostic_info or {},
        }
        super().__init__(message, details=details)
        self.code = ErrorCode.PLANNER_ERROR
        self.stage = stage
        self.operator = operator
        self.node_ref = node_ref
        self.diagnostic_info = diagnostic_info or {}


class UnsupportedQueryError(PlannerError):
    """Raised when a query construct is not supported by the Logical Planner."""

    def __init__(
        self,
        message: str,
        stage: str = "QueryValidation",
        operator: Optional[str] = None,
        node_ref: Optional[str] = None,
        diagnostic_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = {
            "stage": stage,
            "operator": operator,
            "node_ref": node_ref,
            "diagnostic_info": diagnostic_info or {},
        }
        super().__init__(message, details=details)
        self.code = ErrorCode.CAPABILITY_UNSUPPORTED
        self.stage = stage
        self.operator = operator
        self.node_ref = node_ref
        self.diagnostic_info = diagnostic_info or {}


class PlannerInvariantError(PlannerError):
    """Raised when an internal logical planner invariant condition is violated."""

    def __init__(
        self,
        message: str,
        stage: str = "LogicalPlanning",
        operator: Optional[str] = None,
        node_ref: Optional[str] = None,
        diagnostic_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = {
            "stage": stage,
            "operator": operator,
            "node_ref": node_ref,
            "diagnostic_info": diagnostic_info or {},
        }
        super().__init__(message, details=details)
        self.code = ErrorCode.PLANNER_ERROR
        self.stage = stage
        self.operator = operator
        self.node_ref = node_ref
        self.diagnostic_info = diagnostic_info or {}


__all__ = [
    "UnknownOperatorError",
    "LoweringError",
    "LogicalValidationError",
    "UnsupportedQueryError",
    "PlannerInvariantError",
]
