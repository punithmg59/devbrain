"""
core/namespaces/builder.py
--------------------------
NamespaceBuilder Facade Engine for assembling canonical NamespaceTree from List[ParserResult].
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from core.namespaces.diagnostics import NamespaceDiagnostics
from core.namespaces.enums import NamespaceKind
from core.namespaces.ids import generate_scope_namespace_id
from core.namespaces.models import NamespaceNode
from core.namespaces.traversal import ScopeDefinition, ScopeExtractorRegistry
from core.namespaces.tree import NamespaceTree
from core.namespaces.validator import NamespaceTreeValidator
from core.symbols.enums import Language
from core.symbols.ids import NamespaceID
from core.symbols.metadata import Metadata
from core.symbols.models import SourceInformation, SourceLocation, SourceRange
from core.symbols.qualified_name import QualifiedName
from models.parser import ParserResult


class NamespaceBuildOptions(BaseModel):
    """Configuration options for NamespaceBuilder execution."""
    include_anonymous_scopes: bool = Field(default=True, description="Whether to include anonymous/block scopes")
    validate_tree_on_completion: bool = Field(default=True, description="Run integrity validator before returning")

    model_config = {
        "frozen": True
    }


class NamespaceBuilder:
    """
    Facade engine that converts a list of ParserResult AST outputs into a canonical NamespaceTree.
    """

    def __init__(self, options: Optional[NamespaceBuildOptions] = None):
        self.options = options or NamespaceBuildOptions()

    def build_tree(self, parser_results: List[ParserResult], repository_id: str) -> NamespaceTree:
        """
        Main Facade Entrypoint.

        Parameters
        ----------
        parser_results:
            List of ParserResult AST objects from Step 2.
        repository_id:
            Identifier of the repository workspace.

        Returns
        -------
        NamespaceTree
            Immutable, fully indexed, and validated NamespaceTree contract.
        """
        diagnostics = NamespaceDiagnostics()
        nodes_map: Dict[NamespaceID, NamespaceNode] = {}
        fqn_map: Dict[str, NamespaceID] = {}
        file_map: Dict[str, List[NamespaceID]] = {}
        parent_children_map: Dict[NamespaceID, List[NamespaceID]] = {}

        # 1. Create Root Repository Node
        repo_fqn = QualifiedName.from_string("repo")
        root_id = generate_scope_namespace_id(repository_id, Language.FUTURE, None, repo_fqn, NamespaceKind.REPOSITORY)
        
        root_node = NamespaceNode(
            id=root_id,
            fqn=repo_fqn,
            name=repository_id,
            kind=NamespaceKind.REPOSITORY,
            language=Language.FUTURE,
            repository_id=repository_id,
            declaration_order=0
        )
        nodes_map[root_id] = root_node
        fqn_map[repo_fqn.to_string()] = root_id
        parent_children_map[root_id] = []

        package_nodes_map: Dict[str, NamespaceID] = {}

        # 2. Process each ParserResult safely
        for pr in parser_results:
            try:
                self._process_parser_result(
                    pr=pr,
                    repository_id=repository_id,
                    root_id=root_id,
                    nodes_map=nodes_map,
                    fqn_map=fqn_map,
                    file_map=file_map,
                    parent_children_map=parent_children_map,
                    package_nodes_map=package_nodes_map,
                    diagnostics=diagnostics
                )
            except Exception as e:
                diagnostics = diagnostics.add_error(
                    message=f"Error extracting namespaces from file '{pr.file_path}': {str(e)}",
                    file_path=pr.file_path,
                    code="ERR_PARSE_FILE_FAILED"
                )

        # 3. Update parent nodes with immutable children_ids tuples
        final_nodes: Dict[NamespaceID, NamespaceNode] = {}
        for nid, node in nodes_map.items():
            ch_ids = tuple(parent_children_map.get(nid, []))
            final_nodes[nid] = node.with_children(ch_ids)

        tree = NamespaceTree(
            repository_id=repository_id,
            root_id=root_id,
            nodes=final_nodes,
            fqn_index=fqn_map,
            file_index=file_map,
            diagnostics=diagnostics
        )

        # 4. Optional validation check
        if self.options.validate_tree_on_completion:
            val_diags = NamespaceTreeValidator.validate(tree)
            if val_diags.diagnostics:
                all_diags = diagnostics.diagnostics + val_diags.diagnostics
                tree = NamespaceTree(
                    repository_id=tree.repository_id,
                    root_id=tree.root_id,
                    nodes=tree.nodes,
                    fqn_index=tree.fqn_index,
                    file_index=tree.file_index,
                    diagnostics=NamespaceDiagnostics(diagnostics=all_diags)
                )

        return tree

    def _process_parser_result(
        self,
        pr: ParserResult,
        repository_id: str,
        root_id: NamespaceID,
        nodes_map: Dict[NamespaceID, NamespaceNode],
        fqn_map: Dict[str, NamespaceID],
        file_map: Dict[str, List[NamespaceID]],
        parent_children_map: Dict[NamespaceID, List[NamespaceID]],
        package_nodes_map: Dict[str, NamespaceID],
        diagnostics: NamespaceDiagnostics
    ) -> None:
        file_path = pr.file_path
        lang = Language(pr.language.value.lower()) if hasattr(pr.language, "value") else Language.PYTHON

        # Build Package and Module FQN hierarchy
        norm_path = file_path.replace("\\", "/")
        parts = [p for p in norm_path.split("/") if p]
        
        current_parent_id = root_id
        current_fqn = QualifiedName.from_string("repo")

        # Create Package Nodes for directory segments
        pkg_parts = parts[:-1]
        for idx, pkg_name in enumerate(pkg_parts):
            current_fqn = current_fqn.child(pkg_name)
            pkg_fqn_str = current_fqn.to_string()

            if pkg_fqn_str in package_nodes_map:
                current_parent_id = package_nodes_map[pkg_fqn_str]
            else:
                pkg_id = generate_scope_namespace_id(
                    repository_id=repository_id,
                    language=lang,
                    file_path=None,
                    fqn=current_fqn,
                    kind=NamespaceKind.PACKAGE,
                    scope_index=idx
                )
                pkg_node = NamespaceNode(
                    id=pkg_id,
                    fqn=current_fqn,
                    name=pkg_name,
                    kind=NamespaceKind.PACKAGE,
                    language=lang,
                    repository_id=repository_id,
                    parent_id=current_parent_id,
                    declaration_order=idx
                )
                nodes_map[pkg_id] = pkg_node
                fqn_map[pkg_fqn_str] = pkg_id
                package_nodes_map[pkg_fqn_str] = pkg_id
                parent_children_map.setdefault(current_parent_id, []).append(pkg_id)
                parent_children_map[pkg_id] = []
                current_parent_id = pkg_id

        # Create Module Node for file
        filename = parts[-1] if parts else file_path
        mod_name = os.path.splitext(filename)[0]
        mod_fqn = current_fqn.child(mod_name)

        mod_id = generate_scope_namespace_id(
            repository_id=repository_id,
            language=lang,
            file_path=file_path,
            fqn=mod_fqn,
            kind=NamespaceKind.MODULE,
            scope_index=0
        )

        mod_src_info = SourceInformation(
            file_id=pr.result_id,
            file_path=file_path,
            range=SourceRange(
                start=SourceLocation(line=1, column=0),
                end=SourceLocation(line=max(1, pr.statistics.lines_parsed if pr.statistics else 1), column=0)
            )
        )

        mod_node = NamespaceNode(
            id=mod_id,
            fqn=mod_fqn,
            name=mod_name,
            kind=NamespaceKind.MODULE,
            language=lang,
            repository_id=repository_id,
            file_id=pr.result_id,
            file_path=file_path,
            parent_id=current_parent_id,
            source_info=mod_src_info,
            declaration_order=0
        )
        nodes_map[mod_id] = mod_node
        fqn_map[mod_fqn.to_string()] = mod_id
        file_map.setdefault(file_path, []).append(mod_id)
        parent_children_map.setdefault(current_parent_id, []).append(mod_id)
        parent_children_map[mod_id] = []

        # Extract AST child scopes using Language Scope Extractor
        extractor = ScopeExtractorRegistry.get_extractor(lang)
        scope_defs = extractor.extract_scopes(pr)

        # Recursively construct child scopes under Module Node
        self._build_scope_nodes(
            scope_defs=scope_defs,
            parent_node=mod_node,
            repository_id=repository_id,
            file_id=pr.result_id,
            file_path=file_path,
            language=lang,
            nodes_map=nodes_map,
            fqn_map=fqn_map,
            file_map=file_map,
            parent_children_map=parent_children_map
        )

    def _build_scope_nodes(
        self,
        scope_defs: List[ScopeDefinition],
        parent_node: NamespaceNode,
        repository_id: str,
        file_id: str,
        file_path: str,
        language: Language,
        nodes_map: Dict[NamespaceID, NamespaceNode],
        fqn_map: Dict[str, NamespaceID],
        file_map: Dict[str, List[NamespaceID]],
        parent_children_map: Dict[NamespaceID, List[NamespaceID]]
    ) -> None:
        for idx, sdef in enumerate(scope_defs):
            scope_fqn = parent_node.fqn.child(sdef.name)
            
            node_id = generate_scope_namespace_id(
                repository_id=repository_id,
                language=language,
                file_path=file_path,
                fqn=scope_fqn,
                kind=sdef.kind,
                scope_index=idx
            )

            src_info = SourceInformation(
                file_id=file_id,
                file_path=file_path,
                range=SourceRange(
                    start=SourceLocation(line=max(1, sdef.start_line), column=max(0, sdef.start_column), offset=max(0, sdef.start_byte)),
                    end=SourceLocation(line=max(1, sdef.end_line), column=max(0, sdef.end_column), offset=max(0, sdef.end_byte))
                )
            )

            node = NamespaceNode(
                id=node_id,
                fqn=scope_fqn,
                name=sdef.name,
                kind=sdef.kind,
                language=language,
                repository_id=repository_id,
                file_id=file_id,
                file_path=file_path,
                parent_id=parent_node.id,
                source_info=src_info,
                declaration_order=idx,
                metadata=Metadata(language_metadata=sdef.metadata)
            )

            nodes_map[node_id] = node
            fqn_map[scope_fqn.to_string()] = node_id
            file_map.setdefault(file_path, []).append(node_id)
            parent_children_map.setdefault(parent_node.id, []).append(node_id)
            parent_children_map[node_id] = []

            # Recurse children scopes
            if sdef.children:
                self._build_scope_nodes(
                    scope_defs=sdef.children,
                    parent_node=node,
                    repository_id=repository_id,
                    file_id=file_id,
                    file_path=file_path,
                    language=language,
                    nodes_map=nodes_map,
                    fqn_map=fqn_map,
                    file_map=file_map,
                    parent_children_map=parent_children_map
                )
