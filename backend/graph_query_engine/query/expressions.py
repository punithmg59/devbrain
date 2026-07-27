"""
Query Expression AST Hierarchy.
"""

from typing import Any, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class QueryExpression(BaseModel):
    """
    Base immutable query expression AST node.
    """
    model_config = ConfigDict(frozen=True)

    expression_type: str = Field(..., description="Expression type discriminator string")


class LiteralExpression(QueryExpression):
    """Literal constant value expression."""
    expression_type: str = Field(default="LITERAL", description="Discriminator for literal expression")
    value: Any = Field(..., description="Literal python primitive value (str, int, float, bool, None)")
    value_type: str = Field(default="STRING", description="Literal type string descriptor")


class PropertyAccessExpression(QueryExpression):
    """Property or attribute access expression (e.g. node.name)."""
    expression_type: str = Field(default="PROPERTY_ACCESS", description="Discriminator for property access expression")
    target: str = Field(..., description="Target variable or alias name (e.g. 'node')")
    property_name: str = Field(..., description="Accessed property attribute string")


class ComparisonExpression(QueryExpression):
    """Comparison expression (e.g. A = B, X > Y)."""
    expression_type: str = Field(default="COMPARISON", description="Discriminator for comparison expression")
    left: QueryExpression = Field(..., description="Left hand expression operand")
    operator: str = Field(..., description="Comparison operator: '=', '!=', '<', '<=', '>', '>='")
    right: QueryExpression = Field(..., description="Right hand expression operand")


class LogicalExpression(QueryExpression):
    """Logical expression combining sub-expressions (AND, OR, NOT)."""
    expression_type: str = Field(default="LOGICAL", description="Discriminator for logical expression")
    operator: str = Field(..., description="Logical operator: 'AND', 'OR', 'NOT'")
    operands: Tuple[QueryExpression, ...] = Field(..., description="Operand expressions tuple")


class ArithmeticExpression(QueryExpression):
    """Arithmetic operation expression (+, -, *, /)."""
    expression_type: str = Field(default="ARITHMETIC", description="Discriminator for arithmetic expression")
    operator: str = Field(..., description="Arithmetic operator: '+', '-', '*', '/'")
    left: QueryExpression = Field(..., description="Left hand expression")
    right: QueryExpression = Field(..., description="Right hand expression")


class CollectionExpression(QueryExpression):
    """Collection expression (IN, CONTAINS_ANY, CONTAINS_ALL)."""
    expression_type: str = Field(default="COLLECTION", description="Discriminator for collection expression")
    operator: str = Field(..., description="Collection operator: 'IN', 'CONTAINS_ANY', 'CONTAINS_ALL'")
    item: QueryExpression = Field(..., description="Item expression")
    collection: Tuple[QueryExpression, ...] = Field(..., description="Collection items tuple")


class BooleanExpression(QueryExpression):
    """Explicit boolean constant expression."""
    expression_type: str = Field(default="BOOLEAN", description="Discriminator for boolean expression")
    value: bool = Field(..., description="Boolean value True/False")


class NullExpression(QueryExpression):
    """Null constant expression."""
    expression_type: str = Field(default="NULL", description="Discriminator for null expression")


__all__ = [
    "QueryExpression",
    "LiteralExpression",
    "PropertyAccessExpression",
    "ComparisonExpression",
    "LogicalExpression",
    "ArithmeticExpression",
    "CollectionExpression",
    "BooleanExpression",
    "NullExpression",
]
