"""
DevBrain Graph Query Engine - Query Representation Layer Package.

Language-neutral, 100% immutable, strongly typed query representation foundation (Step 4.2).
"""

from graph_query_engine.query.ast import ASTNodeType, QueryAST, QueryASTNode
from graph_query_engine.query.builder import (
    ASTBuilder,
    ExpressionBuilder,
    PredicateBuilder,
    QueryBuilder,
)
from graph_query_engine.query.constraints import (
    ComplexityLimitConstraint,
    MemoryBudgetConstraint,
    NodeBudgetConstraint,
    PlannerConstraint,
    QueryConstraints,
    ResultLimitConstraint,
    TimeBudgetConstraint,
    TraversalBudgetConstraint,
)
from graph_query_engine.query.diagnostics import (
    QueryDiagnosticItem,
    QueryDiagnosticsMetadata,
    SourceLocation,
)
from graph_query_engine.query.expressions import (
    ArithmeticExpression,
    BooleanExpression,
    CollectionExpression,
    ComparisonExpression,
    LiteralExpression,
    LogicalExpression,
    NullExpression,
    PropertyAccessExpression,
    QueryExpression,
)
from graph_query_engine.query.model import (
    EngineeringQuery,
    PlannerQueryOptions,
    QueryMetadata,
    QueryOptions,
    SourceInfo,
)
from graph_query_engine.query.operators import (
    AggregateOperator,
    DeduplicationOperator,
    ExpandOperator,
    FilterOperator,
    GroupingOperator,
    HierarchyOperator,
    ImpactOperator,
    JoinOperator,
    LimitOperator,
    LookupOperator,
    PathOperator,
    ProjectionOperator,
    QueryOperator,
    ReachabilityOperator,
    SortingOperator,
    UsageSearchOperator,
)
from graph_query_engine.query.predicates import (
    AndPredicate,
    AttributePredicate,
    ContainsPredicate,
    EndsWithPredicate,
    EqualityPredicate,
    ExistsPredicate,
    NodePredicate,
    NotPredicate,
    OrPredicate,
    QueryPredicate,
    RangePredicate,
    RelationshipPredicate,
    StartsWithPredicate,
)
from graph_query_engine.query.references import (
    ApiRouteReference,
    ClassReference,
    CrossRepositoryReference,
    EntityReference,
    FileReference,
    FunctionReference,
    InterfaceReference,
    ModuleReference,
    NamespaceReference,
    PackageReference,
    RepositoryReference,
    SymbolReference,
)
from graph_query_engine.query.result import (
    FormattingMetadata,
    ResultAggregation,
    ResultDeduplication,
    ResultGrouping,
    ResultOrdering,
    ResultPagination,
    ResultProjection,
    ResultSpecification,
)
from graph_query_engine.query.serialization import (
    BinaryQuerySerializer,
    JSONQuerySerializer,
    QuerySerializer,
    YAMLQuerySerializer,
)
from graph_query_engine.query.traversal import (
    TerminationCondition,
    TraversalConstraint,
    TraversalDirection,
    TraversalOptions,
    TraversalRequest,
)
from graph_query_engine.query.validation import (
    QueryValidator,
    ValidationReport,
    ValidationViolation,
)
from graph_query_engine.query.version import QueryVersion, VersionMigrationRegistry
from graph_query_engine.query.visitor import (
    BaseQueryVisitor,
    PrintVisitor,
    QueryVisitor,
    ValidationVisitor,
)

__all__ = [
    # Versioning
    "QueryVersion",
    "VersionMigrationRegistry",
    # Diagnostics
    "SourceLocation",
    "QueryDiagnosticItem",
    "QueryDiagnosticsMetadata",
    # References
    "EntityReference",
    "SymbolReference",
    "FileReference",
    "PackageReference",
    "NamespaceReference",
    "ModuleReference",
    "ClassReference",
    "FunctionReference",
    "InterfaceReference",
    "ApiRouteReference",
    "RepositoryReference",
    "CrossRepositoryReference",
    # Expressions
    "QueryExpression",
    "LiteralExpression",
    "PropertyAccessExpression",
    "ComparisonExpression",
    "LogicalExpression",
    "ArithmeticExpression",
    "CollectionExpression",
    "BooleanExpression",
    "NullExpression",
    # Predicates
    "QueryPredicate",
    "AndPredicate",
    "OrPredicate",
    "NotPredicate",
    "EqualityPredicate",
    "RangePredicate",
    "ContainsPredicate",
    "StartsWithPredicate",
    "EndsWithPredicate",
    "ExistsPredicate",
    "RelationshipPredicate",
    "NodePredicate",
    "AttributePredicate",
    # Traversal
    "TraversalDirection",
    "TraversalConstraint",
    "TerminationCondition",
    "TraversalOptions",
    "TraversalRequest",
    # Operators
    "QueryOperator",
    "LookupOperator",
    "ExpandOperator",
    "ImpactOperator",
    "ReachabilityOperator",
    "UsageSearchOperator",
    "HierarchyOperator",
    "PathOperator",
    "AggregateOperator",
    "ProjectionOperator",
    "GroupingOperator",
    "SortingOperator",
    "DeduplicationOperator",
    "LimitOperator",
    "FilterOperator",
    "JoinOperator",
    # Constraints
    "TimeBudgetConstraint",
    "MemoryBudgetConstraint",
    "NodeBudgetConstraint",
    "TraversalBudgetConstraint",
    "ResultLimitConstraint",
    "ComplexityLimitConstraint",
    "PlannerConstraint",
    "QueryConstraints",
    # Result Specification
    "ResultProjection",
    "ResultOrdering",
    "ResultGrouping",
    "ResultAggregation",
    "ResultPagination",
    "ResultDeduplication",
    "FormattingMetadata",
    "ResultSpecification",
    # AST
    "ASTNodeType",
    "QueryASTNode",
    "QueryAST",
    # Model
    "SourceInfo",
    "QueryOptions",
    "PlannerQueryOptions",
    "QueryMetadata",
    "EngineeringQuery",
    # Visitor
    "QueryVisitor",
    "BaseQueryVisitor",
    "PrintVisitor",
    "ValidationVisitor",
    # Validation
    "ValidationViolation",
    "ValidationReport",
    "QueryValidator",
    # Builder
    "ExpressionBuilder",
    "PredicateBuilder",
    "ASTBuilder",
    "QueryBuilder",
    # Serialization
    "QuerySerializer",
    "JSONQuerySerializer",
    "YAMLQuerySerializer",
    "BinaryQuerySerializer",
]
