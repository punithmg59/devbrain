# backend/graph_query_engine/traversal/visitor.py
"""Visitors for inspecting, validating, printing, and visualizing traversal results.
Includes Mermaid graph diagram generator for traversed subgraphs and paths.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List

from .result import TraversalPath, TraversalResult


class TraversalVisitor(abc.ABC):
    """Abstract base class for traversal visitors."""

    @abc.abstractmethod
    def visit_result(self, result: TraversalResult) -> Any:
        """Visit a TraversalResult."""

    @abc.abstractmethod
    def visit_path(self, path: TraversalPath) -> Any:
        """Visit a TraversalPath."""


class TraversalInspectionVisitor(TraversalVisitor):
    """Visitor collecting overview inspection info."""

    def visit_result(self, result: TraversalResult) -> Dict[str, Any]:
        return {
            "visited_node_count": len(result.visited_nodes),
            "visited_edge_count": len(result.visited_edges),
            "path_count": len(result.paths),
            "max_depth": max(result.depth_map.values()) if result.depth_map else 0,
            "roots": result.root_nodes,
        }

    def visit_path(self, path: TraversalPath) -> Dict[str, Any]:
        return {
            "length": len(path.nodes),
            "start": path.start_node,
            "end": path.end_node,
            "depth": path.depth,
        }


class TraversalValidationVisitor(TraversalVisitor):
    """Visitor validating paths and node lists."""

    def __init__(self) -> None:
        self.errors: List[str] = []

    def visit_result(self, result: TraversalResult) -> List[str]:
        if not result.visited_nodes and result.root_nodes:
            self.errors.append("Visited nodes list is empty despite root_nodes being provided")
        for path in result.paths:
            self.visit_path(path)
        return self.errors

    def visit_path(self, path: TraversalPath) -> List[str]:
        if len(path.nodes) < 1:
            self.errors.append("TraversalPath has empty nodes list")
        return self.errors


class TraversalPrintingVisitor(TraversalVisitor):
    """Visitor returning formatted string representation."""

    def visit_result(self, result: TraversalResult) -> str:
        lines = [
            f"=== TraversalResult ({result.execution_time_ms:.2f} ms) ===",
            f"Root Nodes: {result.root_nodes}",
            f"Visited Nodes ({len(result.visited_nodes)}): {result.visited_nodes[:10]}...",
            f"Discovered Paths ({len(result.paths)}):",
        ]
        for p in result.paths[:5]:
            lines.append(f"  {self.visit_path(p)}")
        return "\n".join(lines)

    def visit_path(self, path: TraversalPath) -> str:
        return " -> ".join(path.nodes)


class TraversalStatisticsVisitor(TraversalVisitor):
    """Visitor generating comprehensive numerical statistics."""

    def visit_result(self, result: TraversalResult) -> Dict[str, Any]:
        return {
            "node_count": len(result.visited_nodes),
            "edge_count": len(result.visited_edges),
            "path_count": len(result.paths),
            "duration_ms": result.execution_time_ms,
            "max_depth": max(result.depth_map.values()) if result.depth_map else 0,
            "metrics": result.metrics.model_dump(),
        }

    def visit_path(self, path: TraversalPath) -> Dict[str, Any]:
        return {"nodes": len(path.nodes), "depth": path.depth, "weight": path.weight}


class MermaidGraphVisitor(TraversalVisitor):
    """Visitor that generates Mermaid flowchart markdown for traversed paths and subgraphs."""

    def visit_result(self, result: TraversalResult) -> str:
        lines = ["graph TD"]
        # Add root nodes styling
        for r in result.root_nodes:
            lines.append(f"  {r}[\"Root: {r}\"]")

        # Add path edges
        edge_set = set()
        for path in result.paths:
            for i in range(len(path.nodes) - 1):
                src = path.nodes[i]
                tgt = path.nodes[i + 1]
                pair = (src, tgt)
                if pair not in edge_set:
                    edge_set.add(pair)
                    lines.append(f"  {src} --> {tgt}")

        if len(lines) == 1:
            # Fallback if no paths but visited nodes
            for n in result.visited_nodes:
                lines.append(f"  {n}[\"{n}\"]")

        return "\n".join(lines)

    def visit_path(self, path: TraversalPath) -> str:
        lines = ["graph LR"]
        for i in range(len(path.nodes) - 1):
            lines.append(f"  {path.nodes[i]} --> {path.nodes[i+1]}")
        return "\n".join(lines)


__all__ = [
    "TraversalVisitor",
    "TraversalInspectionVisitor",
    "TraversalValidationVisitor",
    "TraversalPrintingVisitor",
    "TraversalStatisticsVisitor",
    "MermaidGraphVisitor",
]
