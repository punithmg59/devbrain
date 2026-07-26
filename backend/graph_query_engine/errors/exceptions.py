"""
Specific Exception Classes for Graph Query Engine.
"""

from datetime import datetime
from typing import Any, Optional

from graph_query_engine.errors.base import GraphQueryError
from graph_query_engine.errors.codes import ErrorCode


class InitializationError(GraphQueryError):
    """Raised when engine component or lifecycle initialization fails."""
    def __init__(
        self,
        message: str = "Engine initialization failed.",
        code: ErrorCode | str = ErrorCode.INITIALIZATION_FAILED,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class ConfigurationError(GraphQueryError):
    """Raised when engine configuration loading or validation fails."""
    def __init__(
        self,
        message: str = "Invalid engine configuration.",
        code: ErrorCode | str = ErrorCode.CONFIGURATION_INVALID,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class ValidationError(GraphQueryError):
    """Raised when query syntax, parameter, or domain model validation fails."""
    def __init__(
        self,
        message: str = "Query validation failed.",
        code: ErrorCode | str = ErrorCode.VALIDATION_FAILED,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class ExecutionError(GraphQueryError):
    """Raised when an error occurs during query planning or execution."""
    def __init__(
        self,
        message: str = "Query execution error occurred.",
        code: ErrorCode | str = ErrorCode.EXECUTION_FAILED,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class TimeoutError(GraphQueryError):
    """Raised when query execution exceeds the configured budget or timeout."""
    def __init__(
        self,
        message: str = "Query execution timed out.",
        code: ErrorCode | str = ErrorCode.TIMEOUT_EXCEEDED,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class FeatureNotImplementedError(GraphQueryError):
    """Raised when a queried feature, strategy, or capability is not implemented yet."""
    def __init__(
        self,
        message: str = "Requested graph query feature is not implemented.",
        code: ErrorCode | str = ErrorCode.NOT_IMPLEMENTED,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


# Step 3.2 Index Specific Exceptions
class IndexBuildError(GraphQueryError):
    """Raised when constructing an index from GraphView fails."""
    def __init__(
        self,
        message: str = "Failed to build index.",
        code: ErrorCode | str = ErrorCode.INDEX_BUILD_FAILED,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class IndexLookupError(GraphQueryError):
    """Raised when a required key is not found in an index."""
    def __init__(
        self,
        message: str = "Index key lookup failed.",
        code: ErrorCode | str = ErrorCode.INDEX_LOOKUP_FAILED,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class DuplicateNodeError(IndexBuildError):
    """Raised when duplicate NodeIds are encountered during node index build."""
    def __init__(
        self,
        message: str = "Duplicate NodeId encountered during index build.",
        code: ErrorCode | str = ErrorCode.DUPLICATE_NODE_ID,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class DuplicateEdgeError(IndexBuildError):
    """Raised when duplicate EdgeIds are encountered during edge index build."""
    def __init__(
        self,
        message: str = "Duplicate EdgeId encountered during index build.",
        code: ErrorCode | str = ErrorCode.DUPLICATE_EDGE_ID,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class DuplicateSymbolError(IndexBuildError):
    """Raised when duplicate SymbolIds are encountered during symbol index build."""
    def __init__(
        self,
        message: str = "Duplicate SymbolId encountered during index build.",
        code: ErrorCode | str = ErrorCode.DUPLICATE_SYMBOL_ID,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class DuplicateQualifiedNameError(IndexBuildError):
    """Raised when duplicate qualified names are encountered during qualified name index build."""
    def __init__(
        self,
        message: str = "Duplicate qualified name encountered during index build.",
        code: ErrorCode | str = ErrorCode.DUPLICATE_QUALIFIED_NAME,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


# Step 3.3 Relationship Index Specific Exceptions
class InvalidRelationshipError(IndexBuildError):
    """Raised when an invalid relationship specification is encountered."""
    def __init__(
        self,
        message: str = "Invalid relationship specification.",
        code: ErrorCode | str = ErrorCode.INVALID_RELATIONSHIP,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class DanglingEdgeError(IndexBuildError):
    """Raised when an edge references a non-existent source or target node."""
    def __init__(
        self,
        message: str = "Dangling edge detected.",
        code: ErrorCode | str = ErrorCode.DANGLING_EDGE,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class RelationshipIntegrityError(IndexBuildError):
    """Raised when relationship integrity checks fail."""
    def __init__(
        self,
        message: str = "Relationship integrity check failed.",
        code: ErrorCode | str = ErrorCode.RELATIONSHIP_INTEGRITY_FAILED,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class CSRConstructionError(IndexBuildError):
    """Raised when CSR offset construction or sorting fails."""
    def __init__(
        self,
        message: str = "CSR adjacency construction failed.",
        code: ErrorCode | str = ErrorCode.CSR_CONSTRUCTION_FAILED,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class RelationshipLookupError(IndexLookupError):
    """Raised when looking up a relationship fails."""
    def __init__(
        self,
        message: str = "Relationship lookup failed.",
        code: ErrorCode | str = ErrorCode.RELATIONSHIP_LOOKUP_FAILED,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


# Step 3.4 Semantic Index Specific Exceptions
class SemanticIndexError(IndexBuildError):
    """Raised when building a semantic index fails."""
    def __init__(
        self,
        message: str = "Semantic index construction failed.",
        code: ErrorCode | str = ErrorCode.SEMANTIC_INDEX_FAILED,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class InvalidInheritanceError(SemanticIndexError):
    """Raised when invalid inheritance cycles or broken parent references are found."""
    def __init__(
        self,
        message: str = "Invalid inheritance specification.",
        code: ErrorCode | str = ErrorCode.INVALID_INHERITANCE,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class DuplicateRouteError(SemanticIndexError):
    """Raised when duplicate API routes (same method and path) are registered."""
    def __init__(
        self,
        message: str = "Duplicate API route detected.",
        code: ErrorCode | str = ErrorCode.DUPLICATE_ROUTE,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class BrokenReferenceError(SemanticIndexError):
    """Raised when a symbol reference points to a non-existent definition."""
    def __init__(
        self,
        message: str = "Broken symbol reference encountered.",
        code: ErrorCode | str = ErrorCode.BROKEN_REFERENCE,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class InvalidImportError(SemanticIndexError):
    """Raised when an import statement references an invalid module or symbol."""
    def __init__(
        self,
        message: str = "Invalid import reference.",
        code: ErrorCode | str = ErrorCode.INVALID_IMPORT,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class InvalidAnnotationError(SemanticIndexError):
    """Raised when an annotation or decorator specification is invalid."""
    def __init__(
        self,
        message: str = "Invalid annotation specification.",
        code: ErrorCode | str = ErrorCode.INVALID_ANNOTATION,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class MissingInterfaceError(SemanticIndexError):
    """Raised when a required interface type is missing."""
    def __init__(
        self,
        message: str = "Missing interface type.",
        code: ErrorCode | str = ErrorCode.MISSING_INTERFACE,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class MissingParentTypeError(SemanticIndexError):
    """Raised when a parent base type is missing from the type index."""
    def __init__(
        self,
        message: str = "Missing parent base type.",
        code: ErrorCode | str = ErrorCode.MISSING_PARENT_TYPE,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


class DuplicateDefinitionError(SemanticIndexError):
    """Raised when duplicate canonical definitions exist for a symbol."""
    def __init__(
        self,
        message: str = "Duplicate symbol definition detected.",
        code: ErrorCode | str = ErrorCode.DUPLICATE_DEFINITION,
        metadata: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        timestamp: Optional[datetime] = None,
        stack_trace: Optional[str] = None,
    ) -> None:
        super().__init__(message=message, code=code, metadata=metadata, cause=cause, timestamp=timestamp, stack_trace=stack_trace)


NotImplementedError = FeatureNotImplementedError

__all__ = [
    "InitializationError",
    "ConfigurationError",
    "ValidationError",
    "ExecutionError",
    "TimeoutError",
    "FeatureNotImplementedError",
    "NotImplementedError",
    "IndexBuildError",
    "IndexLookupError",
    "DuplicateNodeError",
    "DuplicateEdgeError",
    "DuplicateSymbolError",
    "DuplicateQualifiedNameError",
    "InvalidRelationshipError",
    "DanglingEdgeError",
    "RelationshipIntegrityError",
    "CSRConstructionError",
    "RelationshipLookupError",
    "SemanticIndexError",
    "InvalidInheritanceError",
    "DuplicateRouteError",
    "BrokenReferenceError",
    "InvalidImportError",
    "InvalidAnnotationError",
    "MissingInterfaceError",
    "MissingParentTypeError",
    "DuplicateDefinitionError",
]
