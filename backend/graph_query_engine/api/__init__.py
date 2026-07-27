"""
DevBrain Graph Query Engine - Public Query API Package.

Official internal facade and primary entry point into the DevBrain Graph Query Engine.
Translates high-level engineering questions into internal pipeline execution requests.
"""

from graph_query_engine.api.builder import ApiQueryBuilder
from graph_query_engine.api.context import QueryContext
from graph_query_engine.api.contracts import IQueryEngineAPI
from graph_query_engine.api.engine import QueryEngine
from graph_query_engine.api.errors import QueryErrorCode, QueryErrorDetail
from graph_query_engine.api.exceptions import (
    PublicQueryApiException,
    QueryExecutionException,
    QueryNotFoundException,
    QueryTimeoutException,
    QueryValidationException,
    SessionNotFoundException,
)
from graph_query_engine.api.executor import QueryExecutor
from graph_query_engine.api.factory import QueryFactory
from graph_query_engine.api.options import QueryOptions
from graph_query_engine.api.registry import QueryRegistry
from graph_query_engine.api.request import QueryRequest
from graph_query_engine.api.response import QueryResponse, ResponseStatus
from graph_query_engine.api.result import QueryDiagnostics, QueryResult, QueryStatistics
from graph_query_engine.api.serialization import (
    BinaryQuerySerializer,
    JSONQuerySerializer,
    QuerySerializer,
    YAMLQuerySerializer,
)
from graph_query_engine.api.session import QuerySession, QuerySessionModel
from graph_query_engine.api.validation import (
    QueryValidation,
    QueryValidationReport,
    QueryValidationViolation,
)
from graph_query_engine.api.version import QueryVersion

__all__ = [
    # Main Facade & Session
    "QueryEngine",
    "QuerySession",
    "QuerySessionModel",
    "QueryFactory",
    "QueryRegistry",
    "IQueryEngineAPI",
    # Pipeline Orchestrator & Builder
    "QueryExecutor",
    "ApiQueryBuilder",
    # Data Models & Options
    "QueryContext",
    "QueryOptions",
    "QueryRequest",
    "QueryResponse",
    "ResponseStatus",
    "QueryResult",
    "QueryStatistics",
    "QueryDiagnostics",
    # Validation
    "QueryValidation",
    "QueryValidationReport",
    "QueryValidationViolation",
    # Versioning & Errors
    "QueryVersion",
    "QueryErrorCode",
    "QueryErrorDetail",
    # Exceptions
    "PublicQueryApiException",
    "QueryValidationException",
    "QueryExecutionException",
    "QueryTimeoutException",
    "QueryNotFoundException",
    "SessionNotFoundException",
    # Serialization
    "QuerySerializer",
    "JSONQuerySerializer",
    "YAMLQuerySerializer",
    "BinaryQuerySerializer",
]
