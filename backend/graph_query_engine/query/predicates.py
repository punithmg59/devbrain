"""
Query Predicate AST Hierarchy.
"""

from typing import Any, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.query.expressions import QueryExpression
from graph_query_engine.types import RelationshipType


class QueryPredicate(BaseModel):
    """
    Base immutable predicate AST node.
    """
    model_config = ConfigDict(frozen=True)

    predicate_type: str = Field(..., description="Predicate type discriminator string")


class AndPredicate(QueryPredicate):
    """Logical AND combination of sub-predicates."""
    predicate_type: str = Field(default="AND", description="Discriminator for AND predicate")
    predicates: Tuple[QueryPredicate, ...] = Field(..., description="Tuple of operand predicates")


class OrPredicate(QueryPredicate):
    """Logical OR combination of sub-predicates."""
    predicate_type: str = Field(default="OR", description="Discriminator for OR predicate")
    predicates: Tuple[QueryPredicate, ...] = Field(..., description="Tuple of operand predicates")


class NotPredicate(QueryPredicate):
    """Logical NOT negation of a sub-predicate."""
    predicate_type: str = Field(default="NOT", description="Discriminator for NOT predicate")
    predicate: QueryPredicate = Field(..., description="Negated sub-predicate")


class EqualityPredicate(QueryPredicate):
    """Equality predicate evaluating property == expected_value."""
    predicate_type: str = Field(default="EQUALITY", description="Discriminator for equality predicate")
    property_name: str = Field(..., description="Target property name")
    expected_value: Any = Field(..., description="Expected value")


class RangePredicate(QueryPredicate):
    """Range predicate evaluating min_val <= property <= max_val."""
    predicate_type: str = Field(default="RANGE", description="Discriminator for range predicate")
    property_name: str = Field(..., description="Target property name")
    min_value: Optional[Any] = Field(default=None, description="Minimum bound inclusive")
    max_value: Optional[Any] = Field(default=None, description="Maximum bound inclusive")


class ContainsPredicate(QueryPredicate):
    """Sub-string or collection containment predicate."""
    predicate_type: str = Field(default="CONTAINS", description="Discriminator for contains predicate")
    property_name: str = Field(..., description="Target property name")
    substring: str = Field(..., description="Substring to search for")


class StartsWithPredicate(QueryPredicate):
    """Prefix matching predicate."""
    predicate_type: str = Field(default="STARTS_WITH", description="Discriminator for starts_with predicate")
    property_name: str = Field(..., description="Target property name")
    prefix: str = Field(..., description="Required prefix string")


class EndsWithPredicate(QueryPredicate):
    """Suffix matching predicate."""
    predicate_type: str = Field(default="ENDS_WITH", description="Discriminator for ends_with predicate")
    property_name: str = Field(..., description="Target property name")
    suffix: str = Field(..., description="Required suffix string")


class ExistsPredicate(QueryPredicate):
    """Property existence predicate."""
    predicate_type: str = Field(default="EXISTS", description="Discriminator for property existence predicate")
    property_name: str = Field(..., description="Target property name")


class RelationshipPredicate(QueryPredicate):
    """Predicate evaluating relationship properties or types."""
    predicate_type: str = Field(default="RELATIONSHIP", description="Discriminator for relationship predicate")
    relationship_type: Optional[RelationshipType] = Field(default=None, description="Target RelationshipType enum")
    direction: Optional[str] = Field(default=None, description="Direction constraint: OUTGOING, INCOMING, BOTH")


class NodePredicate(QueryPredicate):
    """Predicate evaluating graph node attributes or types."""
    predicate_type: str = Field(default="NODE", description="Discriminator for node predicate")
    node_type: Optional[str] = Field(default=None, description="Node type constraint (FUNCTION, CLASS, FILE, etc.)")
    expression: Optional[QueryExpression] = Field(default=None, description="Associated filter expression")


class AttributePredicate(QueryPredicate):
    """Generic attribute expression predicate."""
    predicate_type: str = Field(default="ATTRIBUTE", description="Discriminator for attribute predicate")
    attribute_name: str = Field(..., description="Attribute name")
    expression: QueryExpression = Field(..., description="Attribute evaluation expression")


__all__ = [
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
]
