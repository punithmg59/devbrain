"""
core/type_reference_edges/extractor.py
---------------------------------------
Compile-Time Type Reference Extractor from SemanticRepository structures.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.symbol_builder import SemanticRepository
from core.symbols import Language, SourceRange, SymbolID, SymbolKind


class ExtractedTypeReferenceStatement(BaseModel):
    """
    Extracted type reference specification representing a compile-time type dependency.
    """
    source_file_path: str = Field(..., description="Path of source file containing type reference")
    source_symbol_id: SymbolID = Field(..., description="SymbolID of containing symbol (function, parameter, field, variable)")
    referenced_type_raw: str = Field(..., description="Raw referenced type string (e.g. 'User', 'List[User]', 'Promise<User>')")
    context: str = Field(default="field", description="Context of type reference ('parameter', 'return_type', 'field', 'variable', 'generic', 'alias')")
    is_generic: bool = Field(default=False, description="True if reference contains generic type parameters")
    is_nullable: bool = Field(default=False, description="True if type is optional/nullable")
    source_range: Optional[SourceRange] = Field(default=None, description="Source code location range")
    ast_node_ref: Optional[Dict[str, Any]] = Field(default=None, description="Raw parser AST node reference")
    language: Language = Field(..., description="Programming language classification")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }


class TypeReferenceExtractor:
    """
    Discovers and extracts compile-time type references from SemanticRepository structures.
    """

    def extract_type_references(self, repo: SemanticRepository) -> List[ExtractedTypeReferenceStatement]:
        extracted: List[ExtractedTypeReferenceStatement] = []

        # 1. Extract from Canonical Symbols metadata & parameters
        for sym in repo.canonical_symbols.symbols:
            meta_dict = sym.metadata.user_metadata or sym.metadata.language_metadata or sym.metadata.custom if hasattr(sym.metadata, "custom") else {}

            # Return type annotations on functions/methods
            return_type = meta_dict.get("return_type") or meta_dict.get("return_annotation")
            if return_type and isinstance(return_type, str):
                extracted.append(ExtractedTypeReferenceStatement(
                    source_file_path=sym.file_path,
                    source_symbol_id=sym.id,
                    referenced_type_raw=return_type.strip(),
                    context="return_type",
                    is_generic="[" in return_type or "<" in return_type,
                    is_nullable="Optional" in return_type or "?" in return_type,
                    source_range=sym.source_info.range,
                    ast_node_ref=sym.parser_node_ref,
                    language=sym.language
                ))

            # Parameter type annotations
            parameters = meta_dict.get("parameters", []) if isinstance(meta_dict, dict) else []
            for param in parameters:
                if isinstance(param, dict) and param.get("type"):
                    ptype = str(param["type"])
                    extracted.append(ExtractedTypeReferenceStatement(
                        source_file_path=sym.file_path,
                        source_symbol_id=sym.id,
                        referenced_type_raw=ptype.strip(),
                        context="parameter",
                        is_generic="[" in ptype or "<" in ptype,
                        is_nullable="Optional" in ptype or "?" in ptype,
                        source_range=sym.source_info.range,
                        ast_node_ref=sym.parser_node_ref,
                        language=sym.language
                    ))

            # Field / Variable type annotations
            if sym.kind in (SymbolKind.FIELD, SymbolKind.VARIABLE, SymbolKind.CONSTANT, SymbolKind.PROPERTY):
                type_ann = meta_dict.get("type_annotation") or meta_dict.get("type")
                if type_ann and isinstance(type_ann, str):
                    extracted.append(ExtractedTypeReferenceStatement(
                        source_file_path=sym.file_path,
                        source_symbol_id=sym.id,
                        referenced_type_raw=type_ann.strip(),
                        context="field" if sym.kind == SymbolKind.FIELD else "variable",
                        is_generic="[" in type_ann or "<" in type_ann,
                        is_nullable="Optional" in type_ann or "?" in type_ann,
                        source_range=sym.source_info.range,
                        ast_node_ref=sym.parser_node_ref,
                        language=sym.language
                    ))

        # 2. Extract from ParserResult AST roots directly if workspace is attached
        if repo.workspace and hasattr(repo.workspace, "parser_results"):
            for pr in getattr(repo.workspace, "parser_results", []):
                self._extract_ast_type_references(pr, repo, extracted)

        return extracted

    def _extract_ast_type_references(
        self,
        pr: Any,
        repo: SemanticRepository,
        out_list: List[ExtractedTypeReferenceStatement]
    ) -> None:
        ast_root = getattr(pr, "ast_root", None)
        if not isinstance(ast_root, dict):
            return

        file_path = getattr(pr, "file_path", "")

        def walk(node: Dict[str, Any]):
            ntype = str(node.get("type", "")).lower()
            name = str(node.get("name", ""))

            # Check for function definition parameters and return types in AST
            if ntype in ("func_def", "function_definition", "function", "async_func_def") and name:
                matching_syms = repo.symbol_table.get_by_name(name)
                func_sym = None
                for ms in matching_syms:
                    if ms.file_path == file_path:
                        func_sym = ms
                        break

                if func_sym:
                    meta = node.get("metadata") or {}
                    ret = meta.get("return_type") or meta.get("return_annotation") or node.get("return_type")
                    if ret and isinstance(ret, str):
                        out_list.append(ExtractedTypeReferenceStatement(
                            source_file_path=file_path,
                            source_symbol_id=func_sym.id,
                            referenced_type_raw=ret.strip(),
                            context="return_type",
                            is_generic="[" in ret or "<" in ret,
                            is_nullable="Optional" in ret or "?" in ret,
                            ast_node_ref=node,
                            language=Language.PYTHON
                        ))

                    params = meta.get("parameters") or node.get("parameters") or []
                    if isinstance(params, list):
                        for p in params:
                            if isinstance(p, dict) and p.get("type"):
                                ptype = str(p["type"])
                                out_list.append(ExtractedTypeReferenceStatement(
                                    source_file_path=file_path,
                                    source_symbol_id=func_sym.id,
                                    referenced_type_raw=ptype.strip(),
                                    context="parameter",
                                    is_generic="[" in ptype or "<" in ptype,
                                    is_nullable="Optional" in ptype or "?" in ptype,
                                    ast_node_ref=node,
                                    language=Language.PYTHON
                                ))

            for child in node.get("children", []):
                if isinstance(child, dict):
                    walk(child)

        walk(ast_root)
