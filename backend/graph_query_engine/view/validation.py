"""
GraphView Validation Framework.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.view.graph_view import GraphView


class GraphViewValidationViolation(BaseModel):
    """Represents a single GraphView validation rule violation."""
    model_config = ConfigDict(frozen=True)

    category: str = Field(..., description="Validation category name")
    rule_name: str = Field(..., description="Specific rule identifier")
    message: str = Field(..., description="Human-readable violation description")
    severity: str = Field(default="ERROR", description="ERROR or WARNING")


class GraphViewValidationReport(BaseModel):
    """
    Immutable validation quality report for a GraphView instance.
    """
    model_config = ConfigDict(frozen=True)

    is_valid: bool = Field(..., description="True if no ERROR severity violations exist")
    violations: tuple[GraphViewValidationViolation, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of violations",
    )
    validated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of validation execution",
    )


class GraphViewValidator:
    """
    Validator inspecting GraphView across integrity categories and compatibility hooks.
    """

    @classmethod
    def validate(cls, graph_view: Optional[GraphView]) -> GraphViewValidationReport:
        """
        Executes complete validation over graph_view and returns a report.
        """
        violations: list[GraphViewValidationViolation] = []

        # 1. Graph Existence Check
        if graph_view is None:
            violations.append(
                GraphViewValidationViolation(
                    category="EXISTENCE",
                    rule_name="GRAPH_NOT_NULL",
                    message="GraphView instance is null/None.",
                )
            )
            return GraphViewValidationReport(is_valid=False, violations=tuple(violations))

        # 2. Identity & Metadata Validation
        if not graph_view.metadata.identity:
            violations.append(
                GraphViewValidationViolation(
                    category="IDENTITY",
                    rule_name="MISSING_GRAPH_IDENTITY",
                    message="GraphMetadata.identity reference is missing.",
                )
            )

        if not graph_view.metadata.schema_version:
            violations.append(
                GraphViewValidationViolation(
                    category="SCHEMA",
                    rule_name="MISSING_SCHEMA_VERSION",
                    message="GraphMetadata.schema_version must not be empty.",
                )
            )

        # 3. Snapshot Information Validation
        if not graph_view.snapshot.snapshot_id:
            violations.append(
                GraphViewValidationViolation(
                    category="SNAPSHOT",
                    rule_name="MISSING_SNAPSHOT_ID",
                    message="GraphSnapshotInfo.snapshot_id must not be empty.",
                )
            )

        # 4. Node Uniqueness & NodeId Validity
        node_ids = set()
        for node_id, node in graph_view.nodes.items():
            if not node_id:
                violations.append(
                    GraphViewValidationViolation(
                        category="NODE",
                        rule_name="INVALID_NODE_ID",
                        message="NodeId cannot be empty string.",
                    )
                )
            if node_id in node_ids:
                violations.append(
                    GraphViewValidationViolation(
                        category="NODE",
                        rule_name="DUPLICATE_NODE_ID",
                        message=f"Duplicate NodeId found: '{node_id}'.",
                    )
                )
            node_ids.add(node_id)

        # 5. Edge Uniqueness & Source/Target Node Existence
        edge_ids = set()
        for edge_id, edge in graph_view.edges.items():
            if not edge_id:
                violations.append(
                    GraphViewValidationViolation(
                        category="EDGE",
                        rule_name="INVALID_EDGE_ID",
                        message="EdgeId cannot be empty string.",
                    )
                )
            if edge_id in edge_ids:
                violations.append(
                    GraphViewValidationViolation(
                        category="EDGE",
                        rule_name="DUPLICATE_EDGE_ID",
                        message=f"Duplicate EdgeId found: '{edge_id}'.",
                    )
                )
            edge_ids.add(edge_id)

            if edge.source_node_id not in graph_view.nodes:
                violations.append(
                    GraphViewValidationViolation(
                        category="EDGE_REFERENCE",
                        rule_name="DANGLING_SOURCE_NODE",
                        message=f"Edge '{edge_id}' references non-existent source node '{edge.source_node_id}'.",
                    )
                )
            if edge.target_node_id not in graph_view.nodes:
                violations.append(
                    GraphViewValidationViolation(
                        category="EDGE_REFERENCE",
                        rule_name="DANGLING_TARGET_NODE",
                        message=f"Edge '{edge_id}' references non-existent target node '{edge.target_node_id}'.",
                    )
                )

        # 6. Extensible Placeholder Validation Hooks
        cls._validate_schema_compatibility(graph_view, violations)
        cls._validate_graph_version_compatibility(graph_view, violations)
        cls._validate_analyzer_compatibility(graph_view, violations)
        cls._validate_storage_compatibility(graph_view, violations)
        cls._validate_capability_hooks(graph_view, violations)

        is_valid = not any(v.severity == "ERROR" for v in violations)
        return GraphViewValidationReport(is_valid=is_valid, violations=tuple(violations))

    @classmethod
    def _validate_schema_compatibility(cls, graph_view: GraphView, violations: list[GraphViewValidationViolation]) -> None:
        """Placeholder hook for future storage schema compatibility checks."""
        pass

    @classmethod
    def _validate_graph_version_compatibility(cls, graph_view: GraphView, violations: list[GraphViewValidationViolation]) -> None:
        """Placeholder hook for future graph semver version checks."""
        pass

    @classmethod
    def _validate_analyzer_compatibility(cls, graph_view: GraphView, violations: list[GraphViewValidationViolation]) -> None:
        """Placeholder hook for future repository analyzer version checks."""
        pass

    @classmethod
    def _validate_storage_compatibility(cls, graph_view: GraphView, violations: list[GraphViewValidationViolation]) -> None:
        """Placeholder hook for future segment storage layout checks."""
        pass

    @classmethod
    def _validate_capability_hooks(cls, graph_view: GraphView, violations: list[GraphViewValidationViolation]) -> None:
        """Placeholder hook for future capability requirements validation."""
        pass


__all__ = [
    "GraphViewValidationViolation",
    "GraphViewValidationReport",
    "GraphViewValidator",
]
