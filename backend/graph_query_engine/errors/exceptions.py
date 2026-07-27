from typing import Any, Optional
from graph_query_engine.errors.base import GraphQueryError
from graph_query_engine.errors.codes import ErrorCode


class GraphQueryEngineError(GraphQueryError):
    """Base exception for all Graph Query Engine errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode | str = ErrorCode.INITIALIZATION_FAILED,
        details: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        meta = metadata if metadata is not None else details
        super().__init__(message=message, code=code, metadata=meta, cause=cause)
        self.details = self.metadata


class ConfigurationError(GraphQueryEngineError):
    """Raised when configuration validation or loading fails."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None, metadata: Optional[dict[str, Any]] = None, cause: Optional[BaseException] = None) -> None:
        super().__init__(message, code=ErrorCode.CONFIGURATION_INVALID, details=details, metadata=metadata, cause=cause)


class ValidationError(GraphQueryEngineError):
    """Raised when entity or view validation fails."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None, metadata: Optional[dict[str, Any]] = None, cause: Optional[BaseException] = None) -> None:
        super().__init__(message, code=ErrorCode.VALIDATION_FAILED, details=details, metadata=metadata, cause=cause)


class ImmutabilityError(GraphQueryEngineError):
    """Raised when an attempt is made to mutate an immutable structure."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None, metadata: Optional[dict[str, Any]] = None, cause: Optional[BaseException] = None) -> None:
        super().__init__(message, code=ErrorCode.IMMUTABILITY_VIOLATION, details=details, metadata=metadata, cause=cause)


class LifecycleError(GraphQueryEngineError):
    """Raised when an invalid lifecycle state transition is requested."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None, metadata: Optional[dict[str, Any]] = None, cause: Optional[BaseException] = None) -> None:
        super().__init__(message, code=ErrorCode.INVALID_STATE_TRANSITION, details=details, metadata=metadata, cause=cause)


# --- Step 3 Exceptions ---
class DuplicateNodeError(ValidationError):
    """Raised when duplicate node IDs are detected during index build."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.code = ErrorCode.DUPLICATE_NODE


class DuplicateEdgeError(ValidationError):
    """Raised when duplicate edge IDs are detected during index build."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.code = ErrorCode.DUPLICATE_EDGE


class DuplicateSymbolError(ValidationError):
    """Raised when duplicate symbols are detected during index build."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.code = ErrorCode.DUPLICATE_SYMBOL


class DuplicateQualifiedNameError(ValidationError):
    """Raised when duplicate qualified names are detected during index build."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.code = ErrorCode.DUPLICATE_QUALIFIED_NAME


class IndexBuildError(GraphQueryEngineError):
    """Raised when building an index fails."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, code=ErrorCode.INDEX_BUILD_ERROR, details=details)


class IndexLookupError(GraphQueryEngineError):
    """Raised when an index lookup fails or key is not found."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, code=ErrorCode.INDEX_LOOKUP_ERROR, details=details)


class DanglingEdgeError(ValidationError):
    """Raised when an edge references a non-existent source or target node ID."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.code = ErrorCode.DANGLING_EDGE


class CSRConstructionError(IndexBuildError):
    """Raised when CSR index construction fails."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.code = ErrorCode.CSR_CONSTRUCTION_ERROR


class RelationshipLookupError(IndexLookupError):
    """Raised when relationship edge lookup fails."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.code = ErrorCode.RELATIONSHIP_LOOKUP_ERROR


class SemanticIndexError(IndexBuildError):
    """Raised when a semantic index build or validation fails."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.code = ErrorCode.SEMANTIC_INDEX_ERROR


class DuplicateRouteError(SemanticIndexError):
    """Raised when duplicate API routes are detected."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.code = ErrorCode.DUPLICATE_ROUTE


# --- Step 4.1 Planner Infrastructure Exceptions ---
class PlannerError(GraphQueryEngineError):
    """Base exception for all Query Planner errors."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, code=ErrorCode.PLANNER_ERROR, details=details)


class InvalidPlannerStateError(PlannerError):
    """Raised when an invalid state transition occurs in the Planner lifecycle."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.code = ErrorCode.INVALID_PLANNER_STATE


class BudgetExceededError(PlannerError):
    """Raised when planning budget limits (timeout, iterations, memory) are exceeded."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.code = ErrorCode.BUDGET_EXCEEDED


class InvalidPlannerConfigError(PlannerError):
    """Raised when PlannerConfiguration or PlanningBudget is invalid."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.code = ErrorCode.INVALID_PLANNER_CONFIG


class PlannerRegistryError(PlannerError):
    """Raised when registration or lookup in PlannerRegistry fails."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.code = ErrorCode.PLANNER_REGISTRY_ERROR


class CapabilityUnsupportedError(PlannerError):
    """Raised when a requested planner capability is unsupported or disabled."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.code = ErrorCode.CAPABILITY_UNSUPPORTED


class InitializationError(GraphQueryEngineError):
    """Raised when engine initialization fails."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None, metadata: Optional[dict[str, Any]] = None, cause: Optional[BaseException] = None) -> None:
        super().__init__(message, code=ErrorCode.INITIALIZATION_FAILED, details=details, metadata=metadata, cause=cause)


class ExecutionError(GraphQueryEngineError):
    """Raised when query execution fails."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None, metadata: Optional[dict[str, Any]] = None, cause: Optional[BaseException] = None) -> None:
        super().__init__(message, code=ErrorCode.EXECUTION_FAILED, details=details, metadata=metadata, cause=cause)


class TimeoutError(GraphQueryEngineError):
    """Raised when query execution times out."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None, metadata: Optional[dict[str, Any]] = None, cause: Optional[BaseException] = None) -> None:
        super().__init__(message, code=ErrorCode.TIMEOUT_EXCEEDED, details=details, metadata=metadata, cause=cause)


class EngineNotImplementedError(GraphQueryEngineError):
    """Raised when an un-implemented feature contract is invoked."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None, metadata: Optional[dict[str, Any]] = None, cause: Optional[BaseException] = None) -> None:
        super().__init__(message, code=ErrorCode.NOT_IMPLEMENTED, details=details, metadata=metadata, cause=cause)


__all__ = [
    "GraphQueryEngineError",
    "GraphQueryError",
    "ConfigurationError",
    "ValidationError",
    "ImmutabilityError",
    "LifecycleError",
    "InitializationError",
    "ExecutionError",
    "TimeoutError",
    "EngineNotImplementedError",
    "DuplicateNodeError",
    "DuplicateEdgeError",
    "DuplicateSymbolError",
    "DuplicateQualifiedNameError",
    "IndexBuildError",
    "IndexLookupError",
    "DanglingEdgeError",
    "CSRConstructionError",
    "RelationshipLookupError",
    "SemanticIndexError",
    "DuplicateRouteError",
    "PlannerError",
    "InvalidPlannerStateError",
    "BudgetExceededError",
    "InvalidPlannerConfigError",
    "PlannerRegistryError",
    "CapabilityUnsupportedError",
]
