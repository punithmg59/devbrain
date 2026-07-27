"""
AST → Logical Plan Lowering Rules and Pipeline.

Transforms Query AST nodes deterministically into execution-independent Logical Operators.
"""

import uuid
from typing import Any, List, Optional, Protocol, Tuple, runtime_checkable

from graph_query_engine.logical.errors import LoweringError, UnknownOperatorError
from graph_query_engine.logical.operators import (
    LogicalAggregateOperator,
    LogicalDeduplicationOperator,
    LogicalExpandOperator,
    LogicalFilterOperator,
    LogicalGroupingOperator,
    LogicalJoinOperator,
    LogicalLimitOperator,
    LogicalLookupOperator,
    LogicalOperator,
    LogicalProjectionOperator,
    LogicalSortingOperator,
)
from graph_query_engine.logical.plan import LogicalPlanNode
from graph_query_engine.query.ast import QueryASTNode
from graph_query_engine.query.model import EngineeringQuery
from graph_query_engine.query.operators import (
    AggregateOperator,
    DeduplicationOperator,
    ExpandOperator,
    FilterOperator,
    GroupingOperator,
    JoinOperator,
    LimitOperator,
    LookupOperator,
    ProjectionOperator,
    QueryOperator,
    SortingOperator,
)


class ASTLoweringContext:
    """State context container during AST lowering execution."""

    def __init__(self) -> None:
        self.rules_applied: List[str] = []

    def record_rule(self, rule_name: str) -> None:
        """Records a applied lowering rule name."""
        self.rules_applied.append(rule_name)


@runtime_checkable
class ASTLoweringRule(Protocol):
    """Protocol definition for AST node lowering rules."""

    def can_lower(self, ast_node: QueryASTNode) -> bool:
        """Returns True if this rule handles the given AST node."""
        ...

    def lower(
        self,
        ast_node: QueryASTNode,
        children: Tuple[LogicalPlanNode, ...],
        context: ASTLoweringContext,
    ) -> LogicalOperator:
        """Lowers an AST node into a LogicalOperator."""
        ...


class BaseLoweringRule:
    """Base abstract lowering rule implementation."""
    rule_name: str = "BaseLoweringRule"


class LookupLoweringRule(BaseLoweringRule):
    """Lowers LookupOperator AST nodes into LogicalLookupOperator."""
    rule_name = "LookupLoweringRule"

    def can_lower(self, ast_node: QueryASTNode) -> bool:
        return isinstance(ast_node.content, LookupOperator)

    def lower(
        self,
        ast_node: QueryASTNode,
        children: Tuple[LogicalPlanNode, ...],
        context: ASTLoweringContext,
    ) -> LogicalOperator:
        context.record_rule(self.rule_name)
        op: LookupOperator = ast_node.content
        op_id = f"op_lookup_{uuid.uuid4().hex[:8]}"
        output_fields = ("id", "name", "kind")
        return LogicalLookupOperator(
            operator_id=op_id,
            output_schema=output_fields,
            target_reference=op.target_reference,
        )


class ExpandLoweringRule(BaseLoweringRule):
    """Lowers ExpandOperator AST nodes into LogicalExpandOperator."""
    rule_name = "ExpandLoweringRule"

    def can_lower(self, ast_node: QueryASTNode) -> bool:
        return isinstance(ast_node.content, ExpandOperator)

    def lower(
        self,
        ast_node: QueryASTNode,
        children: Tuple[LogicalPlanNode, ...],
        context: ASTLoweringContext,
    ) -> LogicalOperator:
        context.record_rule(self.rule_name)
        op: ExpandOperator = ast_node.content
        op_id = f"op_expand_{uuid.uuid4().hex[:8]}"
        output_fields = ("source_id", "target_id", "relationship_type")
        return LogicalExpandOperator(
            operator_id=op_id,
            output_schema=output_fields,
            traversal_request=op.traversal_request,
        )


class FilterLoweringRule(BaseLoweringRule):
    """Lowers FilterOperator AST nodes into LogicalFilterOperator."""
    rule_name = "FilterLoweringRule"

    def can_lower(self, ast_node: QueryASTNode) -> bool:
        return isinstance(ast_node.content, FilterOperator)

    def lower(
        self,
        ast_node: QueryASTNode,
        children: Tuple[LogicalPlanNode, ...],
        context: ASTLoweringContext,
    ) -> LogicalOperator:
        context.record_rule(self.rule_name)
        op: FilterOperator = ast_node.content
        op_id = f"op_filter_{uuid.uuid4().hex[:8]}"
        output_fields = children[0].operator.output_schema if children else ()
        return LogicalFilterOperator(
            operator_id=op_id,
            output_schema=output_fields,
            predicate=op.predicate,
        )


class ProjectionLoweringRule(BaseLoweringRule):
    """Lowers ProjectionOperator AST nodes into LogicalProjectionOperator."""
    rule_name = "ProjectionLoweringRule"

    def can_lower(self, ast_node: QueryASTNode) -> bool:
        return isinstance(ast_node.content, ProjectionOperator)

    def lower(
        self,
        ast_node: QueryASTNode,
        children: Tuple[LogicalPlanNode, ...],
        context: ASTLoweringContext,
    ) -> LogicalOperator:
        context.record_rule(self.rule_name)
        op: ProjectionOperator = ast_node.content
        op_id = f"op_project_{uuid.uuid4().hex[:8]}"
        return LogicalProjectionOperator(
            operator_id=op_id,
            output_schema=op.fields,
            projected_fields=op.fields,
        )


class AggregateLoweringRule(BaseLoweringRule):
    """Lowers AggregateOperator AST nodes into LogicalAggregateOperator."""
    rule_name = "AggregateLoweringRule"

    def can_lower(self, ast_node: QueryASTNode) -> bool:
        return isinstance(ast_node.content, AggregateOperator)

    def lower(
        self,
        ast_node: QueryASTNode,
        children: Tuple[LogicalPlanNode, ...],
        context: ASTLoweringContext,
    ) -> LogicalOperator:
        context.record_rule(self.rule_name)
        op: AggregateOperator = ast_node.content
        op_id = f"op_agg_{uuid.uuid4().hex[:8]}"
        alias = op.alias or f"{op.function_name.lower()}_val"
        return LogicalAggregateOperator(
            operator_id=op_id,
            output_schema=(alias,),
            function_name=op.function_name,
            expression=op.expression,
            result_alias=alias,
        )


class GroupingLoweringRule(BaseLoweringRule):
    """Lowers GroupingOperator AST nodes into LogicalGroupingOperator."""
    rule_name = "GroupingLoweringRule"

    def can_lower(self, ast_node: QueryASTNode) -> bool:
        return isinstance(ast_node.content, GroupingOperator)

    def lower(
        self,
        ast_node: QueryASTNode,
        children: Tuple[LogicalPlanNode, ...],
        context: ASTLoweringContext,
    ) -> LogicalOperator:
        context.record_rule(self.rule_name)
        op: GroupingOperator = ast_node.content
        op_id = f"op_group_{uuid.uuid4().hex[:8]}"
        return LogicalGroupingOperator(
            operator_id=op_id,
            output_schema=op.group_keys,
            group_keys=op.group_keys,
        )


class SortingLoweringRule(BaseLoweringRule):
    """Lowers SortingOperator AST nodes into LogicalSortingOperator."""
    rule_name = "SortingLoweringRule"

    def can_lower(self, ast_node: QueryASTNode) -> bool:
        return isinstance(ast_node.content, SortingOperator)

    def lower(
        self,
        ast_node: QueryASTNode,
        children: Tuple[LogicalPlanNode, ...],
        context: ASTLoweringContext,
    ) -> LogicalOperator:
        context.record_rule(self.rule_name)
        op: SortingOperator = ast_node.content
        op_id = f"op_sort_{uuid.uuid4().hex[:8]}"
        output_fields = children[0].operator.output_schema if children else ()
        return LogicalSortingOperator(
            operator_id=op_id,
            output_schema=output_fields,
            field_name=op.field_name,
            ascending=op.ascending,
        )


class DeduplicationLoweringRule(BaseLoweringRule):
    """Lowers DeduplicationOperator AST nodes into LogicalDeduplicationOperator."""
    rule_name = "DeduplicationLoweringRule"

    def can_lower(self, ast_node: QueryASTNode) -> bool:
        return isinstance(ast_node.content, DeduplicationOperator)

    def lower(
        self,
        ast_node: QueryASTNode,
        children: Tuple[LogicalPlanNode, ...],
        context: ASTLoweringContext,
    ) -> LogicalOperator:
        context.record_rule(self.rule_name)
        op: DeduplicationOperator = ast_node.content
        op_id = f"op_dedup_{uuid.uuid4().hex[:8]}"
        output_fields = children[0].operator.output_schema if children else ()
        return LogicalDeduplicationOperator(
            operator_id=op_id,
            output_schema=output_fields,
            distinct_fields=op.target_fields,
        )


class LimitLoweringRule(BaseLoweringRule):
    """Lowers LimitOperator AST nodes into LogicalLimitOperator."""
    rule_name = "LimitLoweringRule"

    def can_lower(self, ast_node: QueryASTNode) -> bool:
        return isinstance(ast_node.content, LimitOperator)

    def lower(
        self,
        ast_node: QueryASTNode,
        children: Tuple[LogicalPlanNode, ...],
        context: ASTLoweringContext,
    ) -> LogicalOperator:
        context.record_rule(self.rule_name)
        op: LimitOperator = ast_node.content
        op_id = f"op_limit_{uuid.uuid4().hex[:8]}"
        output_fields = children[0].operator.output_schema if children else ()
        return LogicalLimitOperator(
            operator_id=op_id,
            output_schema=output_fields,
            limit=op.limit,
            offset=op.offset,
        )


class JoinLoweringRule(BaseLoweringRule):
    """Lowers JoinOperator AST nodes into LogicalJoinOperator."""
    rule_name = "JoinLoweringRule"

    def can_lower(self, ast_node: QueryASTNode) -> bool:
        return isinstance(ast_node.content, JoinOperator)

    def lower(
        self,
        ast_node: QueryASTNode,
        children: Tuple[LogicalPlanNode, ...],
        context: ASTLoweringContext,
    ) -> LogicalOperator:
        context.record_rule(self.rule_name)
        op: JoinOperator = ast_node.content
        op_id = f"op_join_{uuid.uuid4().hex[:8]}"
        left_fields = children[0].operator.output_schema if len(children) > 0 else ()
        right_fields = children[1].operator.output_schema if len(children) > 1 else ()
        output_fields = tuple(dict.fromkeys(left_fields + right_fields))
        return LogicalJoinOperator(
            operator_id=op_id,
            output_schema=output_fields,
            join_type=op.join_type,
            on_predicate=op.on_predicate,
        )


class ASTLoweringPipeline:
    """
    Pipeline transformer executing AST → LogicalPlanNode tree transformations.
    """

    def __init__(self) -> None:
        self.rules: List[ASTLoweringRule] = [
            LookupLoweringRule(),
            ExpandLoweringRule(),
            FilterLoweringRule(),
            ProjectionLoweringRule(),
            AggregateLoweringRule(),
            GroupingLoweringRule(),
            SortingLoweringRule(),
            DeduplicationLoweringRule(),
            LimitLoweringRule(),
            JoinLoweringRule(),
        ]

    def lower_query(self, query: EngineeringQuery) -> Tuple[LogicalPlanNode, ASTLoweringContext]:
        """
        Lowers an EngineeringQuery AST into a LogicalPlanNode tree root.
        """
        context = ASTLoweringContext()
        root_plan_node = self._lower_node(query.ast.root_node, context)

        # Apply result_spec projection if defined and not already projected
        proj_fields = query.result_spec.projection.projected_fields
        if proj_fields and root_plan_node.operator.operator_name != "LOGICAL_PROJECTION":
            op_id = f"op_project_{uuid.uuid4().hex[:8]}"
            proj_op = LogicalProjectionOperator(
                operator_id=op_id,
                output_schema=proj_fields,
                projected_fields=proj_fields,
            )
            pnode_id = f"lnode_{uuid.uuid4().hex[:8]}"
            root_plan_node = LogicalPlanNode(
                node_id=pnode_id,
                operator=proj_op,
                children=(root_plan_node,),
            )
            context.record_rule("ProjectionResultSpecLoweringRule")

        return root_plan_node, context

    def _lower_node(self, ast_node: QueryASTNode, context: ASTLoweringContext) -> LogicalPlanNode:
        # Recursively lower children first (bottom-up tree construction)
        child_plan_nodes: List[LogicalPlanNode] = []
        for child in ast_node.children:
            child_plan_nodes.append(self._lower_node(child, context))

        children_tuple = tuple(child_plan_nodes)

        # Match lowering rule
        for rule in self.rules:
            if rule.can_lower(ast_node):
                op = rule.lower(ast_node, children_tuple, context)
                pnode_id = f"lnode_{uuid.uuid4().hex[:8]}"
                return LogicalPlanNode(
                    node_id=pnode_id,
                    operator=op,
                    children=children_tuple,
                )

        content_type = type(ast_node.content).__name__
        raise UnknownOperatorError(
            message=f"No AST lowering rule registered for node content '{content_type}'.",
            stage="ASTLowering",
            operator=content_type,
            node_ref=ast_node.node_id,
        )


__all__ = [
    "ASTLoweringContext",
    "ASTLoweringRule",
    "BaseLoweringRule",
    "LookupLoweringRule",
    "ExpandLoweringRule",
    "FilterLoweringRule",
    "ProjectionLoweringRule",
    "AggregateLoweringRule",
    "GroupingLoweringRule",
    "SortingLoweringRule",
    "DeduplicationLoweringRule",
    "LimitLoweringRule",
    "JoinLoweringRule",
    "ASTLoweringPipeline",
]
