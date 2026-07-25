"""
core/symbol_extractor/python_extractor.py
-----------------------------------------
Python-specific AST Symbol Extractor implementation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from core.namespaces.tree import NamespaceTree
from core.symbol_extractor.models import RawSymbol, generate_temporary_id
from core.symbol_extractor.registry import AbstractSymbolExtractor
from core.symbol_extractor.tree_integration import NamespaceResolver
from core.symbols import (
    Accessibility,
    Attribute,
    Documentation,
    Language,
    Metadata,
    ModifierKind,
    ModifierSet,
    QualifiedName,
    SourceInformation,
    SourceLocation,
    SourceRange,
    SymbolKind,
    Visibility,
)
from models.parser import ParserResult


class PythonSymbolExtractor(AbstractSymbolExtractor):
    """
    Extracts Python code declarations from ParserResult AST payloads.
    """

    def extract(
        self,
        parser_result: ParserResult,
        tree: NamespaceTree,
        repository_id: str
    ) -> List[RawSymbol]:
        ast_root = parser_result.ast_root
        if not ast_root:
            return []

        symbols: List[RawSymbol] = []
        file_path = parser_result.file_path
        file_id = parser_result.result_id
        lang = Language.PYTHON

        declaration_counter = 0

        def walk(node: Dict[str, Any] | Any, parent_kind: Optional[SymbolKind] = None) -> None:
            nonlocal declaration_counter
            if not node:
                return

            ndict = node.model_dump() if hasattr(node, "model_dump") else (node if isinstance(node, dict) else {})
            ntype = str(ndict.get("type", "")).lower()
            name = ndict.get("name") or ""
            rdata = ndict.get("range", {}) or {}

            sloc = rdata.get("start", {}) if isinstance(rdata, dict) else getattr(rdata, "start", {})
            eloc = rdata.get("end", {}) if isinstance(rdata, dict) else getattr(rdata, "end", {})

            s_line = getattr(sloc, "line", 1) if not isinstance(sloc, dict) else sloc.get("line", 1)
            s_col = getattr(sloc, "column", 0) if not isinstance(sloc, dict) else sloc.get("column", 0)
            e_line = getattr(eloc, "line", 1) if not isinstance(eloc, dict) else eloc.get("line", 1)
            e_col = getattr(eloc, "column", 0) if not isinstance(eloc, dict) else eloc.get("column", 0)

            s_byte = rdata.get("start_byte", 0) if isinstance(rdata, dict) else getattr(rdata, "start_byte", 0) or 0
            e_byte = rdata.get("end_byte", 0) if isinstance(rdata, dict) else getattr(rdata, "end_byte", 0) or 0

            # Classify declaration
            sym_kind: Optional[SymbolKind] = None
            is_async = False

            if ntype in ("class", "class_definition", "class_def") and name:
                sym_kind = SymbolKind.CLASS
            elif ntype in ("function", "function_definition", "func_def") and name:
                sym_kind = SymbolKind.METHOD if parent_kind == SymbolKind.CLASS else SymbolKind.FUNCTION
            elif ntype in ("async_function_definition", "async_func_def") and name:
                sym_kind = SymbolKind.METHOD if parent_kind == SymbolKind.CLASS else SymbolKind.FUNCTION
                is_async = True
            elif ntype in ("assignment", "assign", "ann_assign", "variable_declaration") and name:
                sym_kind = SymbolKind.CONSTANT if name.isupper() else (SymbolKind.FIELD if parent_kind == SymbolKind.CLASS else SymbolKind.VARIABLE)
            elif ntype in ("import", "import_from", "import_statement"):
                sym_kind = SymbolKind.IMPORT
                if not name:
                    name = ndict.get("value") or "import"
            elif ntype in ("type_alias", "type_alias_statement") and name:
                sym_kind = SymbolKind.TYPE_ALIAS

            if sym_kind and name:
                declaration_counter += 1
                
                # Resolve containing NamespaceID
                nid = NamespaceResolver.resolve_containing_namespace(
                    tree=tree,
                    file_path=file_path,
                    start_line=s_line,
                    start_column=s_col
                )

                parent_ns_node = tree.get_node(nid)
                candidate_fqn = parent_ns_node.fqn.child(name) if parent_ns_node else QualifiedName.from_string(name)

                temp_id = generate_temporary_id(
                    repository_id=repository_id,
                    file_path=file_path,
                    namespace_id=nid,
                    name=name,
                    kind=sym_kind,
                    declaration_order=declaration_counter
                )

                src_info = SourceInformation(
                    file_id=file_id,
                    file_path=file_path,
                    range=SourceRange(
                        start=SourceLocation(line=max(1, s_line), column=max(0, s_col), offset=max(0, s_byte)),
                        end=SourceLocation(line=max(1, e_line), column=max(0, e_col), offset=max(0, e_byte))
                    ),
                    parser_node_ref={"type": ntype}
                )

                # Extract docstring and decorators if available
                doc_str = ndict.get("docstring") or (ndict.get("metadata", {}).get("docstring") if isinstance(ndict.get("metadata"), dict) else None)
                doc_obj = Documentation(summary=doc_str) if doc_str else None

                decorators = ndict.get("decorators") or (ndict.get("metadata", {}).get("decorators", []) if isinstance(ndict.get("metadata"), dict) else [])
                attributes = [Attribute(name=d if isinstance(d, str) else str(d)) for d in decorators]

                mods = ModifierSet()
                if is_async:
                    mods = mods.with_modifier(ModifierKind.ASYNC)
                if name.startswith("_") and not name.startswith("__"):
                    vis = Visibility.protected()
                elif name.startswith("__") and not name.endswith("__"):
                    vis = Visibility.private()
                else:
                    vis = Visibility.public()

                raw_sym = RawSymbol(
                    temp_id=temp_id,
                    kind=sym_kind,
                    name=name,
                    qualified_name_candidate=candidate_fqn,
                    namespace_id=nid,
                    language=lang,
                    repository_id=repository_id,
                    file_id=file_id,
                    file_path=file_path,
                    parser_result_id=parser_result.result_id,
                    source_info=src_info,
                    declaration_order=declaration_counter,
                    visibility=vis,
                    accessibility=Accessibility.read_write(),
                    modifiers=mods,
                    doc=doc_obj,
                    attributes=attributes,
                    type_annotation=ndict.get("type_annotation"),
                    parser_node_ref={"python_node_type": ntype},
                    metadata=Metadata(language_metadata={"python_node_type": ntype})
                )

                symbols.append(raw_sym)

                # Recurse children
                children = ndict.get("children", []) or ndict.get("body", []) or []
                if isinstance(children, list):
                    for ch in children:
                        walk(ch, parent_kind=sym_kind)
            else:
                children = ndict.get("children", []) or ndict.get("body", []) or []
                if isinstance(children, list):
                    for ch in children:
                        walk(ch, parent_kind=parent_kind)

        walk(ast_root)
        return symbols
