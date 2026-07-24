"""
analysis/call_graph/validation_rules.py
----------------------------------------
Phase 4.8.3 — Modular Read-Only Graph Validation Rules.

Implements isolated, linear-time O(V + E) validation rules for inspecting
CallGraph and GraphIndex objects across 6 categories:
1. StructuralIntegrityRule
2. NodeValidationRule
3. EdgeValidationRule
4. IndexValidationRule
5. GraphConsistencyRule
6. ReferenceIntegrityRule

Design Principles
-----------------
- **Strictly Read-Only**: Inspects data contracts without mutating nodes, edges, or indexes.
- **Isolated & Modular**: Each rule subclass derives from `BaseValidationRule` and can be
  executed independently.
- **No Throwing**: Issues are categorized into `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  `ValidationIssue` objects instead of throwing exceptions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set

from models.graph_models import CallGraph, CallGraphEdge, CallGraphNode
from models.graph_index_models import GraphIndex
from models.graph_validation_models import ValidationIssue, ValidationSeverity


class BaseValidationRule(ABC):
    """Abstract base class for modular graph validation rules."""

    @property
    @abstractmethod
    def category(self) -> str:
        """Category name for issues produced by this rule."""
        pass

    @abstractmethod
    def validate(
        self,
        graph: CallGraph,
        graph_index: Optional[GraphIndex] = None,
    ) -> List[ValidationIssue]:
        """
        Execute read-only validation logic over the graph and index.

        Parameters
        ----------
        graph:
            Source `CallGraph` object.
        graph_index:
            Optional pre-computed `GraphIndex` object.

        Returns
        -------
        List[ValidationIssue]
        """
        pass


class StructuralIntegrityRule(BaseValidationRule):
    """Validates structural initialization of CallGraph and GraphIndex containers."""

    @property
    def category(self) -> str:
        return "StructuralIntegrity"

    def validate(
        self,
        graph: CallGraph,
        graph_index: Optional[GraphIndex] = None,
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        if graph is None:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    code="NULL_CALL_GRAPH",
                    category=self.category,
                    message="CallGraph object is None",
                )
            )
            return issues

        if graph.nodes is None:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    code="UNINITIALIZED_NODES",
                    category=self.category,
                    message="CallGraph.nodes container is None",
                )
            )

        if graph.edges is None:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    code="UNINITIALIZED_EDGES",
                    category=self.category,
                    message="CallGraph.edges container is None",
                )
            )

        if graph.adjacency_list is None:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="UNINITIALIZED_ADJACENCY",
                    category=self.category,
                    message="CallGraph.adjacency_list is None",
                )
            )

        if graph.reverse_adjacency_list is None:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="UNINITIALIZED_REVERSE_ADJACENCY",
                    category=self.category,
                    message="CallGraph.reverse_adjacency_list is None",
                )
            )

        if graph_index is not None:
            if graph_index.node_by_symbol_id is None:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="UNINITIALIZED_INDEX_SYMBOL_ID",
                        category=self.category,
                        message="GraphIndex.node_by_symbol_id is None",
                    )
                )
            if graph_index.node_by_fqn is None:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="UNINITIALIZED_INDEX_FQN",
                        category=self.category,
                        message="GraphIndex.node_by_fqn is None",
                    )
                )

        return issues


class NodeValidationRule(BaseValidationRule):
    """Validates correctness and completeness of all nodes in CallGraph."""

    @property
    def category(self) -> str:
        return "Node"

    def validate(
        self,
        graph: CallGraph,
        graph_index: Optional[GraphIndex] = None,
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not graph or not graph.nodes:
            return issues

        seen_fqns: Dict[str, str] = {}

        for sym_id, node in graph.nodes.items():
            # 1. Missing or Mismatched SymbolId
            if not sym_id or not node.symbol_id:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="MISSING_SYMBOL_ID",
                        category=self.category,
                        message="Node or dict key has empty/missing symbol_id",
                        target_id=sym_id or getattr(node, "symbol_id", None),
                    )
                )
            elif sym_id != node.symbol_id:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="SYMBOL_ID_KEY_MISMATCH",
                        category=self.category,
                        message=f"Node key '{sym_id}' does not match node.symbol_id '{node.symbol_id}'",
                        target_id=sym_id,
                    )
                )

            # 2. Missing or Empty Name
            if not node.name:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="EMPTY_NODE_NAME",
                        category=self.category,
                        message=f"Node '{sym_id}' has empty symbol name",
                        target_id=sym_id,
                        location=node.file_path,
                    )
                )

            # 3. Missing Fully Qualified Name
            if not node.fully_qualified_name:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="MISSING_FQN",
                        category=self.category,
                        message=f"Node '{sym_id}' ('{node.name}') is missing fully_qualified_name",
                        target_id=sym_id,
                        location=node.file_path,
                    )
                )

            # 4. Invalid Node Type
            if not node.node_type:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="INVALID_NODE_TYPE",
                        category=self.category,
                        message=f"Node '{sym_id}' has empty node_type classification",
                        target_id=sym_id,
                    )
                )

            # 5. Missing File Path for non-external symbols
            if not node.file_path and not node.is_external:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        code="MISSING_FILE_PATH",
                        category=self.category,
                        message=f"Internal node '{sym_id}' does not specify source file_path",
                        target_id=sym_id,
                    )
                )

        return issues


class EdgeValidationRule(BaseValidationRule):
    """Validates correctness of directed edges in CallGraph."""

    @property
    def category(self) -> str:
        return "Edge"

    def validate(
        self,
        graph: CallGraph,
        graph_index: Optional[GraphIndex] = None,
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not graph or not graph.edges:
            return issues

        for edge_id, edge in graph.edges.items():
            # 1. Missing Caller or Callee
            if not edge.caller_symbol_id:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="MISSING_CALLER_SYMBOL_ID",
                        category=self.category,
                        message=f"Edge '{edge_id}' has missing caller_symbol_id",
                        target_id=edge_id,
                        location=edge.file_path,
                    )
                )

            if not edge.callee_symbol_id:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="MISSING_CALLEE_SYMBOL_ID",
                        category=self.category,
                        message=f"Edge '{edge_id}' has missing callee_symbol_id",
                        target_id=edge_id,
                        location=edge.file_path,
                    )
                )

            # 2. Endpoint Existence Check
            if edge.caller_symbol_id and edge.caller_symbol_id not in graph.nodes:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="CALLER_DOES_NOT_EXIST",
                        category=self.category,
                        message=f"Edge '{edge_id}' caller symbol_id '{edge.caller_symbol_id}' does not exist in graph nodes",
                        target_id=edge.caller_symbol_id,
                        location=edge.file_path,
                    )
                )

            if edge.callee_symbol_id and edge.callee_symbol_id not in graph.nodes:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="CALLEE_DOES_NOT_EXIST",
                        category=self.category,
                        message=f"Edge '{edge_id}' callee symbol_id '{edge.callee_symbol_id}' does not exist in graph nodes",
                        target_id=edge.callee_symbol_id,
                        location=edge.file_path,
                    )
                )

            # 3. Invalid Weight
            if edge.weight < 1:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="INVALID_EDGE_WEIGHT",
                        category=self.category,
                        message=f"Edge '{edge_id}' has non-positive weight ({edge.weight})",
                        target_id=edge_id,
                    )
                )

            # 4. Self-loop Info Recording
            if edge.caller_symbol_id and edge.caller_symbol_id == edge.callee_symbol_id:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        code="SELF_LOOP_RECURSION",
                        category=self.category,
                        message=f"Edge '{edge_id}' represents recursive self-call on '{edge.caller_symbol_id}'",
                        target_id=edge.caller_symbol_id,
                        location=edge.file_path,
                    )
                )

        return issues


class IndexValidationRule(BaseValidationRule):
    """Validates 100% consistency between GraphIndex lookup tables and CallGraph."""

    @property
    def category(self) -> str:
        return "Index"

    def validate(
        self,
        graph: CallGraph,
        graph_index: Optional[GraphIndex] = None,
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not graph_index:
            return issues

        # 1. Symbol ID index completeness
        for sym_id, node in graph_index.node_by_symbol_id.items():
            if sym_id not in graph.nodes:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="INDEXED_NODE_MISSING",
                        category=self.category,
                        message=f"GraphIndex.node_by_symbol_id contains symbol_id '{sym_id}' missing from CallGraph",
                        target_id=sym_id,
                    )
                )

        # 2. FQN index completeness
        for fqn, node in graph_index.node_by_fqn.items():
            if node.symbol_id not in graph.nodes:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="INDEXED_FQN_MISSING",
                        category=self.category,
                        message=f"GraphIndex.node_by_fqn '{fqn}' maps to symbol_id '{node.symbol_id}' missing from CallGraph",
                        target_id=node.symbol_id,
                    )
                )

        # 3. File index check
        for file_path, nodes in graph_index.nodes_by_file.items():
            for n in nodes:
                if n.symbol_id not in graph.nodes:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="INDEXED_FILE_NODE_MISSING",
                            category=self.category,
                            message=f"File index '{file_path}' contains node '{n.symbol_id}' missing from CallGraph",
                            target_id=n.symbol_id,
                            location=file_path,
                        )
                    )

        return issues


class GraphConsistencyRule(BaseValidationRule):
    """Validates count consistency across graph metadata, nodes, edges, and index tables."""

    @property
    def category(self) -> str:
        return "GraphConsistency"

    def validate(
        self,
        graph: CallGraph,
        graph_index: Optional[GraphIndex] = None,
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not graph:
            return issues

        # 1. Node Count Mismatch
        if graph.node_count != len(graph.nodes):
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="NODE_COUNT_MISMATCH",
                    category=self.category,
                    message=f"CallGraph.node_count ({graph.node_count}) does not match len(nodes) ({len(graph.nodes)})",
                )
            )

        # 2. Edge Count Mismatch
        if graph.edge_count != len(graph.edges):
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="EDGE_COUNT_MISMATCH",
                    category=self.category,
                    message=f"CallGraph.edge_count ({graph.edge_count}) does not match len(edges) ({len(graph.edges)})",
                )
            )

        # 3. Index Size Mismatch
        if graph_index and len(graph_index.node_by_symbol_id) != len(graph.nodes):
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="INDEX_NODE_COUNT_MISMATCH",
                    category=self.category,
                    message=f"GraphIndex indexed nodes ({len(graph_index.node_by_symbol_id)}) does not match CallGraph nodes ({len(graph.nodes)})",
                )
            )

        return issues


class ReferenceIntegrityRule(BaseValidationRule):
    """Validates zero dangling references and forward/reverse adjacency list symmetry."""

    @property
    def category(self) -> str:
        return "ReferenceIntegrity"

    def validate(
        self,
        graph: CallGraph,
        graph_index: Optional[GraphIndex] = None,
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not graph:
            return issues

        # 1. Forward Adjacency symmetry check (u -> v implies v <- u in reverse_adjacency)
        for caller_id, callees in graph.adjacency_list.items():
            if caller_id not in graph.nodes:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="DANGLING_ADJACENCY_CALLER",
                        category=self.category,
                        message=f"Forward adjacency contains caller '{caller_id}' missing from graph nodes",
                        target_id=caller_id,
                    )
                )

            for callee_id in callees:
                if callee_id not in graph.nodes:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="DANGLING_ADJACENCY_CALLEE",
                            category=self.category,
                            message=f"Forward adjacency for '{caller_id}' contains callee '{callee_id}' missing from graph nodes",
                            target_id=callee_id,
                        )
                    )
                else:
                    rev_callers = graph.reverse_adjacency_list.get(callee_id, [])
                    if caller_id not in rev_callers:
                        issues.append(
                            ValidationIssue(
                                severity=ValidationSeverity.ERROR,
                                code="ASYMMETRIC_ADJACENCY",
                                category=self.category,
                                message=f"Forward edge '{caller_id}' -> '{callee_id}' is missing from reverse adjacency list",
                                target_id=caller_id,
                            )
                        )

        return issues
