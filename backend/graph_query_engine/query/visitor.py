"""
Generic Visitor Pattern Infrastructure for Query AST Traversal.
"""

from typing import Any, List, Protocol, runtime_checkable

from graph_query_engine.query.ast import QueryAST, QueryASTNode
from graph_query_engine.query.expressions import QueryExpression
from graph_query_engine.query.operators import QueryOperator
from graph_query_engine.query.predicates import QueryPredicate
from graph_query_engine.query.references import EntityReference


@runtime_checkable
class QueryVisitor(Protocol):
    """
    Protocol definition for Query Representation AST Visitors.
    """

    def visit_query(self, query: Any) -> Any:
        """Visits root EngineeringQuery model."""
        ...

    def visit_ast(self, ast_tree: QueryAST) -> Any:
        """Visits QueryAST root tree."""
        ...

    def visit_node(self, node: QueryASTNode) -> Any:
        """Visits an individual QueryASTNode."""
        ...


class BaseQueryVisitor:
    """
    Abstract base class providing default depth-first traversal of Query ASTs.
    """

    def visit_query(self, query: Any) -> Any:
        """Visits EngineeringQuery and dispatches to its AST."""
        if hasattr(query, "ast"):
            return query.ast.accept(self)
        elif hasattr(query, "root_node"):
            return query.root_node.accept(self)
        return query.accept(self)

    def visit_ast(self, ast_tree: QueryAST) -> Any:
        """Visits QueryAST and dispatches to root_node."""
        return ast_tree.root_node.accept(self)

    def visit_node(self, node: QueryASTNode) -> Any:
        """Visits QueryASTNode and recursively visits all child nodes."""
        results = [self.visit_content(node.content)]
        for child in node.children:
            results.append(child.accept(self))
        return results

    def visit_content(self, content: Any) -> Any:
        """Dispatches content payload based on its type."""
        if isinstance(content, QueryOperator):
            return self.visit_operator(content)
        elif isinstance(content, QueryExpression):
            return self.visit_expression(content)
        elif isinstance(content, QueryPredicate):
            return self.visit_predicate(content)
        elif isinstance(content, EntityReference):
            return self.visit_reference(content)
        return content

    def visit_operator(self, operator: QueryOperator) -> Any:
        """Default handler for QueryOperator nodes."""
        return operator.operator_type

    def visit_expression(self, expression: QueryExpression) -> Any:
        """Default handler for QueryExpression nodes."""
        return expression.expression_type

    def visit_predicate(self, predicate: QueryPredicate) -> Any:
        """Default handler for QueryPredicate nodes."""
        return predicate.predicate_type

    def visit_reference(self, reference: EntityReference) -> Any:
        """Default handler for EntityReference nodes."""
        return reference.reference_type


class PrintVisitor(BaseQueryVisitor):
    """
    AST Visitor that formats and prints a human-readable text tree representation.
    """

    def __init__(self) -> None:
        self._lines: List[str] = []
        self._indent: int = 0

    def print_tree(self, target: Any) -> str:
        """Renders string representation of target (EngineeringQuery, QueryAST, or QueryASTNode)."""
        self._lines.clear()
        self._indent = 0
        if hasattr(target, "accept"):
            target.accept(self)
        else:
            self.visit_query(target)
        return "\n".join(self._lines)

    def visit_node(self, node: QueryASTNode) -> Any:
        prefix = "  " * self._indent
        self._lines.append(f"{prefix}- ASTNode({node.node_id}, type={node.node_type})")
        self._indent += 1
        super().visit_node(node)
        self._indent -= 1


class ValidationVisitor(BaseQueryVisitor):
    """
    AST Visitor collecting structural validation errors across AST nodes.
    """

    def __init__(self) -> None:
        self.errors: List[str] = []

    def validate(self, query: Any) -> List[str]:
        """Executes validation traversal returning error messages list."""
        self.errors.clear()
        self.visit_query(query)
        return list(self.errors)

    def visit_node(self, node: QueryASTNode) -> Any:
        errs = node.validate_node()
        self.errors.extend(errs)
        return super().visit_node(node)


__all__ = [
    "QueryVisitor",
    "BaseQueryVisitor",
    "PrintVisitor",
    "ValidationVisitor",
]
