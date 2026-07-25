"""
core/namespaces/validator.py
----------------------------
Structural Integrity Validator for NamespaceTree.
"""

from __future__ import annotations

from typing import Set

from core.namespaces.diagnostics import NamespaceDiagnostics
from core.namespaces.enums import NamespaceKind
from core.namespaces.tree import NamespaceTree
from core.symbols.ids import NamespaceID


class NamespaceTreeValidator:
    """
    Validates structural consistency and topological integrity of a NamespaceTree.
    """

    @classmethod
    def validate(cls, tree: NamespaceTree) -> NamespaceDiagnostics:
        diagnostics = NamespaceDiagnostics()

        # 1. Root node check
        root = tree.nodes.get(tree.root_id)
        if not root:
            diagnostics = diagnostics.add_error(
                f"Root NamespaceID '{tree.root_id}' is missing from tree nodes map.",
                code="ERR_MISSING_ROOT"
            )
            return diagnostics

        if root.kind != NamespaceKind.REPOSITORY:
            diagnostics = diagnostics.add_warning(
                f"Root node kind is '{root.kind}', expected '{NamespaceKind.REPOSITORY}'.",
                code="WARN_ROOT_KIND"
            )

        # 2. Check each node parent-child integrity
        for nid, node in tree.nodes.items():
            # Check parent exists (unless root)
            if nid != tree.root_id:
                if not node.parent_id:
                    diagnostics = diagnostics.add_error(
                        f"Non-root node '{nid}' ({node.fqn}) has no parent_id.",
                        file_path=node.file_path,
                        code="ERR_DANGLING_NODE"
                    )
                elif node.parent_id not in tree.nodes:
                    diagnostics = diagnostics.add_error(
                        f"Node '{nid}' references non-existent parent_id '{node.parent_id}'.",
                        file_path=node.file_path,
                        code="ERR_MISSING_PARENT"
                    )

            # Check children exist
            for cid in node.children_ids:
                if cid not in tree.nodes:
                    diagnostics = diagnostics.add_error(
                        f"Node '{nid}' ({node.fqn}) references non-existent child_id '{cid}'.",
                        file_path=node.file_path,
                        code="ERR_MISSING_CHILD"
                    )
                else:
                    child_node = tree.nodes[cid]
                    if child_node.parent_id != nid:
                        diagnostics = diagnostics.add_error(
                            f"Child '{cid}' parent_id '{child_node.parent_id}' mismatch with parent '{nid}'.",
                            file_path=node.file_path,
                            code="ERR_PARENT_MISMATCH"
                        )

            # 3. Check for circular parent cycles
            visited: Set[NamespaceID] = set()
            curr = node
            cycle_detected = False
            while curr and curr.parent_id:
                if curr.id in visited:
                    cycle_detected = True
                    break
                visited.add(curr.id)
                curr = tree.nodes.get(curr.parent_id)

            if cycle_detected:
                diagnostics = diagnostics.add_error(
                    f"Circular ancestry parent loop detected starting at node '{nid}' ({node.fqn}).",
                    file_path=node.file_path,
                    code="ERR_CIRCULAR_ANCESTRY"
                )

        return diagnostics
