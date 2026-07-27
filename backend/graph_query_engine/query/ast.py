"""
Query AST Root Framework and Composite Node Models.
"""

from enum import StrEnum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.query.diagnostics import SourceLocation
from graph_query_engine.query.expressions import QueryExpression
from graph_query_engine.query.operators import QueryOperator
from graph_query_engine.query.predicates import QueryPredicate
from graph_query_engine.query.references import EntityReference


class ASTNodeType(StrEnum):
    """AST node classification enum."""
    OPERATOR = "OPERATOR"
    EXPRESSION = "EXPRESSION"
    PREDICATE = "PREDICATE"
    REFERENCE = "REFERENCE"
    ROOT = "ROOT"


class QueryASTNode(BaseModel):
    """
    Abstract immutable AST node representing any node in an EngineeringQuery AST tree.
    """
    model_config = ConfigDict(frozen=True)

    node_id: str = Field(..., description="Unique AST node ID within query tree")
    node_type: ASTNodeType = Field(..., description="AST node category classification")
    location: Optional[SourceLocation] = Field(default=None, description="Source code location metadata")
    content: Union[QueryOperator, QueryExpression, QueryPredicate, EntityReference, Any] = Field(
        ..., description="Wrapped node payload content model"
    )
    children: Tuple["QueryASTNode", ...] = Field(default_factory=tuple, description="Immutable tuple of child AST nodes")

    def accept(self, visitor: Any) -> Any:
        """
        Visitor pattern entrypoint dispatching to visitor.visit_node(self).
        """
        return visitor.visit_node(self)

    def validate_node(self) -> List[str]:
        """
        Performs self-validation returning a list of validation error strings (empty if valid).
        """
        errors: List[str] = []
        if not self.node_id:
            errors.append("ASTNode must have a non-empty node_id.")
        if self.content is None:
            errors.append(f"ASTNode '{self.node_id}' content cannot be None.")
        for child in self.children:
            errors.extend(child.validate_node())
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serializes AST node tree to a dictionary representation."""
        return self.model_dump(mode="python")


class QueryAST(BaseModel):
    """
    Immutable root tree container for a complete Query AST.
    """
    model_config = ConfigDict(frozen=True)

    ast_id: str = Field(..., description="Unique AST identifier string")
    root_node: QueryASTNode = Field(..., description="Root node of the AST tree")
    node_count: int = Field(default=1, ge=1, description="Total node count in tree")

    def accept(self, visitor: Any) -> Any:
        """Dispatches visitor to root node."""
        return visitor.visit_ast(self)

    def validate_ast(self) -> List[str]:
        """Validates entire AST tree."""
        return self.root_node.validate_node()


__all__ = [
    "ASTNodeType",
    "QueryASTNode",
    "QueryAST",
]
