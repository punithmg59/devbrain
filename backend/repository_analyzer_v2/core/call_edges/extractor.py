"""
core/call_edges/extractor.py
-----------------------------
Call Expression Extractor from SemanticRepository AST structures.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.symbol_builder import SemanticRepository
from core.symbols import Language, SourceLocation, SourceRange, SymbolID, SymbolKind


class ExtractedCallStatement(BaseModel):
    """
    Extracted call expression specification representing a single function or method invocation.
    """
    source_file_path: str = Field(..., description="Path of source file containing call")
    caller_symbol_id: SymbolID = Field(..., description="SymbolID of invoking caller scope (function/method)")
    callee_expression_raw: str = Field(..., description="Raw call expression string")
    callee_name: str = Field(..., description="Unqualified invoked name (e.g. 'save', 'login')")
    receiver_expression: Optional[str] = Field(default=None, description="Optional receiver object/class name (e.g. 'self', 'user_service')")
    is_constructor: bool = Field(default=False, description="True if constructor call ('new User()')")
    is_static: bool = Field(default=False, description="True if static method invocation ('User.find')")
    source_range: Optional[SourceRange] = Field(default=None, description="Source code location range")
    ast_node_ref: Optional[Dict[str, Any]] = Field(default=None, description="Raw parser AST node reference")
    language: Language = Field(..., description="Programming language classification")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }


class CallExtractor:
    """
    Discovers and extracts call expressions from SemanticRepository structures.
    """

    def extract_calls(self, repo: SemanticRepository) -> List[ExtractedCallStatement]:
        extracted: List[ExtractedCallStatement] = []

        if repo.workspace and hasattr(repo.workspace, "parser_results"):
            for pr in getattr(repo.workspace, "parser_results", []):
                self._extract_ast_calls(pr, repo, extracted)

        # Also extract from canonical symbols metadata if call references were attached
        for sym in repo.canonical_symbols.symbols:
            if sym.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
                calls = sym.metadata.custom.get("calls", []) if hasattr(sym.metadata, "custom") else []
                for call_dict in calls:
                    if isinstance(call_dict, dict) and "callee" in call_dict:
                        extracted.append(ExtractedCallStatement(
                            source_file_path=sym.file_path,
                            caller_symbol_id=sym.id,
                            callee_expression_raw=call_dict.get("callee", ""),
                            callee_name=call_dict.get("name", call_dict.get("callee", "")),
                            receiver_expression=call_dict.get("receiver"),
                            is_constructor=bool(call_dict.get("is_constructor", False)),
                            is_static=bool(call_dict.get("is_static", False)),
                            source_range=sym.source_info.range,
                            ast_node_ref=sym.parser_node_ref,
                            language=sym.language
                        ))

        return extracted

    def _extract_ast_calls(
        self,
        pr: Any,
        repo: SemanticRepository,
        out_list: List[ExtractedCallStatement]
    ) -> None:
        ast_root = getattr(pr, "ast_root", None)
        if not isinstance(ast_root, dict):
            return

        file_path = getattr(pr, "file_path", "")
        file_syms = repo.symbol_table.get_file_symbols(file_path)
        if not file_syms:
            return
        default_caller_id = file_syms[0].id

        def walk(node: Dict[str, Any], current_caller_id: SymbolID):
            ntype = str(node.get("type", "")).lower()
            name = str(node.get("name", ""))

            # Update caller scope if entering a function or method node
            active_caller_id = current_caller_id
            if ntype in ("function_definition", "func_def", "method_definition", "async_func_def") and name:
                matching_syms = repo.symbol_table.get_by_name(name)
                for ms in matching_syms:
                    if ms.file_path == file_path:
                        active_caller_id = ms.id
                        break

            if ntype in ("call", "call_expression", "method_invocation", "invocation_expression"):
                callee_expr = node.get("function") or node.get("callee") or node.get("name") or "call"
                callee_str = str(callee_expr)
                
                parts = callee_str.split(".")
                receiver = parts[0] if len(parts) > 1 else None
                callee_name = parts[-1]

                out_list.append(ExtractedCallStatement(
                    source_file_path=file_path,
                    caller_symbol_id=active_caller_id,
                    callee_expression_raw=callee_str,
                    callee_name=callee_name,
                    receiver_expression=receiver,
                    is_constructor=bool(node.get("is_constructor", False)),
                    is_static=bool(node.get("is_static", False)),
                    ast_node_ref=node,
                    language=Language.PYTHON
                ))

            for child in node.get("children", []):
                if isinstance(child, dict):
                    walk(child, active_caller_id)

        walk(ast_root, default_caller_id)
