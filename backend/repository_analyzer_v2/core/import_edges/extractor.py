"""
core/import_edges/extractor.py
-------------------------------
Import Statement Extractor from SemanticRepository AST structures and RawSymbols.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.symbol_builder import SemanticRepository
from core.symbols import Language, SourceRange, SymbolID, SymbolKind


class ExtractedImportStatement(BaseModel):
    """
    Extracted import statement specification representing a single import declaration.
    """
    source_file_path: str = Field(..., description="Path of source file containing import")
    source_symbol_id: SymbolID = Field(..., description="SymbolID of importing scope (e.g., module or package)")
    imported_target_raw: str = Field(..., description="Raw import target specification string")
    alias: Optional[str] = Field(default=None, description="Optional imported alias name")
    is_relative: bool = Field(default=False, description="True if import uses relative path syntax")
    relative_level: int = Field(default=0, ge=0, description="Relative depth level (1 for '.', 2 for '..')")
    is_wildcard: bool = Field(default=False, description="True if wildcard/star import ('import *')")
    source_range: Optional[SourceRange] = Field(default=None, description="Source code location range")
    ast_node_ref: Optional[Dict[str, Any]] = Field(default=None, description="Raw parser AST node reference")
    language: Language = Field(..., description="Programming language classification")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }


class ImportExtractor:
    """
    Discovers and extracts raw import statements from SemanticRepository structures.
    """

    def extract_imports(self, repo: SemanticRepository) -> List[ExtractedImportStatement]:
        extracted: List[ExtractedImportStatement] = []

        # 1. Extract from Canonical Symbols of SymbolKind.IMPORT
        for sym in repo.canonical_symbols.symbols:
            if sym.kind == SymbolKind.IMPORT:
                # Resolve containing module symbol or file scope
                mod_syms = repo.symbol_table.get_file_symbols(sym.file_path)
                scope_id = mod_syms[0].id if mod_syms else sym.id

                meta_dict = sym.metadata.user_metadata or sym.metadata.language_metadata or {}
                target_name = meta_dict.get("import_target", sym.name)
                is_rel = meta_dict.get("is_relative", False)
                rel_lvl = meta_dict.get("relative_level", 0)
                alias_name = meta_dict.get("alias", None)
                is_wild = meta_dict.get("is_wildcard", False)

                stmt = ExtractedImportStatement(
                    source_file_path=sym.file_path,
                    source_symbol_id=scope_id,
                    imported_target_raw=target_name,
                    alias=alias_name,
                    is_relative=is_rel,
                    relative_level=rel_lvl,
                    is_wildcard=is_wild,
                    source_range=sym.source_info.range,
                    ast_node_ref=sym.parser_node_ref,
                    language=sym.language
                )
                extracted.append(stmt)

        # 2. Extract from ParserResult AST roots directly if present
        if repo.workspace and hasattr(repo.workspace, "parser_results"):
            for pr in getattr(repo.workspace, "parser_results", []):
                self._extract_ast_imports(pr, repo, extracted)

        return extracted

    def _extract_ast_imports(
        self,
        pr: Any,
        repo: SemanticRepository,
        out_list: List[ExtractedImportStatement]
    ) -> None:
        ast_root = getattr(pr, "ast_root", None)
        if not isinstance(ast_root, dict):
            return

        file_path = getattr(pr, "file_path", "")
        file_syms = repo.symbol_table.get_file_symbols(file_path)
        if not file_syms:
            return
        scope_id = file_syms[0].id

        def walk(node: Dict[str, Any]):
            ntype = str(node.get("type", "")).lower()
            if ntype in ("import_statement", "import_from_statement", "import_declaration", "use_declaration"):
                raw_target = node.get("name") or node.get("module") or node.get("value", "")
                if raw_target:
                    out_list.append(ExtractedImportStatement(
                        source_file_path=file_path,
                        source_symbol_id=scope_id,
                        imported_target_raw=str(raw_target),
                        alias=node.get("alias"),
                        is_relative=bool(node.get("is_relative", False)),
                        relative_level=int(node.get("relative_level", 0)),
                        is_wildcard=bool(node.get("is_wildcard", False)),
                        ast_node_ref=node,
                        language=Language.PYTHON
                    ))
            for child in node.get("children", []):
                if isinstance(child, dict):
                    walk(child)

        walk(ast_root)
