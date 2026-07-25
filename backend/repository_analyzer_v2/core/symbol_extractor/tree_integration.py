"""
core/symbol_extractor/tree_integration.py
-----------------------------------------
NamespaceTree spatial mapping service for binding declarations to NamespaceIDs.
"""

from __future__ import annotations

from typing import List, Optional

from core.namespaces.models import NamespaceNode
from core.namespaces.tree import NamespaceTree
from core.symbols.ids import NamespaceID


class NamespaceResolver:
    """
    Resolves the exact containing NamespaceID from a NamespaceTree for a given source range.
    """

    @classmethod
    def resolve_containing_namespace(
        cls,
        tree: NamespaceTree,
        file_path: str,
        start_line: int,
        start_column: int
    ) -> NamespaceID:
        """
        Find the narrowest/deepest NamespaceNode in file_path containing (start_line, start_column).

        Fallback order:
        1. Narrowest scope in file containing position.
        2. Module node for file.
        3. Repository root node.
        """
        file_nodes = tree.get_nodes_by_file(file_path)
        if not file_nodes:
            return tree.root_id

        matching_nodes: List[NamespaceNode] = []
        for node in file_nodes:
            if node.source_info and node.source_info.range:
                s_range = node.source_info.range
                if (s_range.start.line < start_line or (s_range.start.line == start_line and s_range.start.column <= start_column)):
                    if (s_range.end.line > start_line or (s_range.end.line == start_line and s_range.end.column >= start_column)):
                        matching_nodes.append(node)

        if not matching_nodes:
            # Fallback to module node for file if present
            mod_nodes = [n for n in file_nodes if n.kind.value == "module"]
            return mod_nodes[0].id if mod_nodes else file_nodes[0].id

        # Pick the deepest matching node (maximum depth / longest ancestry)
        best_node = max(matching_nodes, key=lambda n: len(tree.get_ancestors(n.id)))
        return best_node.id
