"""
core/inheritance_edges/extractor.py
------------------------------------
Base Class, Interface, and Trait Inheritance Extractor from SemanticRepository structures.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.symbol_builder import SemanticRepository
from core.symbols import Language, SourceRange, SymbolID, SymbolKind


class ExtractedInheritanceStatement(BaseModel):
    """
    Extracted inheritance statement specification representing a single base class or interface relationship.
    """
    source_file_path: str = Field(..., description="Path of source file containing inheritance declaration")
    derived_symbol_id: SymbolID = Field(..., description="SymbolID of child class/struct")
    base_type_raw: str = Field(..., description="Raw base class or interface type string (e.g. 'User', 'BaseService')")
    is_interface: bool = Field(default=False, description="True if implementing an interface")
    is_trait: bool = Field(default=False, description="True if implementing a Rust/Scala trait")
    is_mixin: bool = Field(default=False, description="True if extending a mixin class")
    source_range: Optional[SourceRange] = Field(default=None, description="Source code location range")
    ast_node_ref: Optional[Dict[str, Any]] = Field(default=None, description="Raw parser AST node reference")
    language: Language = Field(..., description="Programming language classification")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }


class InheritanceExtractor:
    """
    Discovers and extracts base class and interface implementation declarations from SemanticRepository.
    """

    def extract_inheritance(self, repo: SemanticRepository) -> List[ExtractedInheritanceStatement]:
        extracted: List[ExtractedInheritanceStatement] = []

        # 1. Extract from Canonical Symbols of Class/Interface/Struct kinds
        for sym in repo.canonical_symbols.symbols:
            if sym.kind in (SymbolKind.CLASS, SymbolKind.INTERFACE, SymbolKind.STRUCT):
                meta_dict = sym.metadata.user_metadata or sym.metadata.language_metadata or sym.metadata.custom if hasattr(sym.metadata, "custom") else {}
                
                # Base classes (Inheritance)
                base_classes = meta_dict.get("base_classes", []) if isinstance(meta_dict, dict) else []
                for base_raw in base_classes:
                    if base_raw and isinstance(base_raw, str):
                        extracted.append(ExtractedInheritanceStatement(
                            source_file_path=sym.file_path,
                            derived_symbol_id=sym.id,
                            base_type_raw=base_raw.strip(),
                            is_interface=False,
                            is_trait=False,
                            is_mixin="mixin" in base_raw.lower(),
                            source_range=sym.source_info.range,
                            ast_node_ref=sym.parser_node_ref,
                            language=sym.language
                        ))

                # Interfaces (Implementation)
                interfaces = meta_dict.get("interfaces", []) if isinstance(meta_dict, dict) else []
                for iface_raw in interfaces:
                    if iface_raw and isinstance(iface_raw, str):
                        extracted.append(ExtractedInheritanceStatement(
                            source_file_path=sym.file_path,
                            derived_symbol_id=sym.id,
                            base_type_raw=iface_raw.strip(),
                            is_interface=True,
                            is_trait=False,
                            is_mixin=False,
                            source_range=sym.source_info.range,
                            ast_node_ref=sym.parser_node_ref,
                            language=sym.language
                        ))

        # 2. Extract from ParserResult AST roots directly if workspace is attached
        if repo.workspace and hasattr(repo.workspace, "parser_results"):
            for pr in getattr(repo.workspace, "parser_results", []):
                self._extract_ast_inheritance(pr, repo, extracted)

        return extracted

    def _extract_ast_inheritance(
        self,
        pr: Any,
        repo: SemanticRepository,
        out_list: List[ExtractedInheritanceStatement]
    ) -> None:
        ast_root = getattr(pr, "ast_root", None)
        if not isinstance(ast_root, dict):
            return

        file_path = getattr(pr, "file_path", "")

        def walk(node: Dict[str, Any]):
            ntype = str(node.get("type", "")).lower()
            name = str(node.get("name", ""))

            if ntype in ("class_def", "class_definition", "class") and name:
                matching_syms = repo.symbol_table.get_by_name(name)
                class_sym = None
                for ms in matching_syms:
                    if ms.file_path == file_path and ms.kind in (SymbolKind.CLASS, SymbolKind.INTERFACE, SymbolKind.STRUCT):
                        class_sym = ms
                        break

                if class_sym:
                    superclasses = node.get("superclasses") or node.get("bases") or node.get("heritage")
                    if isinstance(superclasses, list):
                        for base_name in superclasses:
                            if isinstance(base_name, str) and base_name:
                                out_list.append(ExtractedInheritanceStatement(
                                    source_file_path=file_path,
                                    derived_symbol_id=class_sym.id,
                                    base_type_raw=base_name,
                                    is_interface=False,
                                    ast_node_ref=node,
                                    language=Language.PYTHON
                                ))
                            elif isinstance(base_name, dict) and base_name.get("name"):
                                out_list.append(ExtractedInheritanceStatement(
                                    source_file_path=file_path,
                                    derived_symbol_id=class_sym.id,
                                    base_type_raw=str(base_name["name"]),
                                    is_interface=False,
                                    ast_node_ref=node,
                                    language=Language.PYTHON
                                ))

            for child in node.get("children", []):
                if isinstance(child, dict):
                    walk(child)

        walk(ast_root)
