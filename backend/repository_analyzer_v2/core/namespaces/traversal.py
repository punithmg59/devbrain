"""
core/namespaces/traversal.py
----------------------------
Language-Agnostic Scope Traversal Framework and Python Scope Extractor implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.namespaces.enums import NamespaceKind
from core.namespaces.exceptions import NamespaceTraversalError
from core.symbols.enums import Language
from models.parser import ParserResult


class ScopeDefinition(BaseModel):
    """
    Extracted scope boundary specification discovered during AST traversal.
    """
    name: str = Field(..., description="Scope identifier name")
    kind: NamespaceKind = Field(..., description="NamespaceKind boundary classification")
    start_line: int = Field(default=1, ge=1)
    start_column: int = Field(default=0, ge=0)
    end_line: int = Field(default=1, ge=1)
    end_column: int = Field(default=0, ge=0)
    start_byte: int = Field(default=0, ge=0)
    end_byte: int = Field(default=0, ge=0)
    children: List[ScopeDefinition] = Field(default_factory=list, description="Nested child scope definitions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible AST node metadata")

    model_config = {
        "arbitrary_types_allowed": True
    }


class AbstractScopeExtractor(ABC):
    """
    Abstract interface for language-specific AST Scope Extractors.
    """

    @abstractmethod
    def extract_scopes(self, parser_result: ParserResult) -> List[ScopeDefinition]:
        """
        Extract top-level scope definitions from a ParserResult AST.
        """
        pass


class PythonScopeExtractor(AbstractScopeExtractor):
    """
    Python-specific AST Scope Extractor.
    Extracts module, class, function, method, lambda, and comprehension scopes from Python ParserResult AST payloads.
    """

    def extract_scopes(self, parser_result: ParserResult) -> List[ScopeDefinition]:
        ast_root = parser_result.ast_root
        if not ast_root:
            return []

        scopes: List[ScopeDefinition] = []
        
        # Traverse AST node dict or ASTNode model payload
        self._walk_node(ast_root, scopes, parent_kind=NamespaceKind.MODULE)
        return scopes

    def _walk_node(self, node: Dict[str, Any] | Any, out_scopes: List[ScopeDefinition], parent_kind: NamespaceKind) -> None:
        if not node:
            return

        node_dict = node.model_dump() if hasattr(node, "model_dump") else (node if isinstance(node, dict) else {})
        node_type = str(node_dict.get("type", "")).lower()
        node_name = node_dict.get("name") or "anonymous"
        range_data = node_dict.get("range", {}) or {}

        start_loc = range_data.get("start", {}) if isinstance(range_data, dict) else getattr(range_data, "start", {})
        end_loc = range_data.get("end", {}) if isinstance(range_data, dict) else getattr(range_data, "end", {})
        
        s_line = getattr(start_loc, "line", 1) if not isinstance(start_loc, dict) else start_loc.get("line", 1)
        s_col = getattr(start_loc, "column", 0) if not isinstance(start_loc, dict) else start_loc.get("column", 0)
        e_line = getattr(end_loc, "line", 1) if not isinstance(end_loc, dict) else end_loc.get("line", 1)
        e_col = getattr(end_loc, "column", 0) if not isinstance(end_loc, dict) else end_loc.get("column", 0)

        s_byte = range_data.get("start_byte", 0) if isinstance(range_data, dict) else getattr(range_data, "start_byte", 0) or 0
        e_byte = range_data.get("end_byte", 0) if isinstance(range_data, dict) else getattr(range_data, "end_byte", 0) or 0

        # Classify scope
        scope_kind: Optional[NamespaceKind] = None
        if node_type in ("class", "class_definition", "class_def"):
            scope_kind = NamespaceKind.CLASS
        elif node_type in ("function", "function_definition", "async_function_definition", "func_def"):
            scope_kind = NamespaceKind.METHOD if parent_kind == NamespaceKind.CLASS else NamespaceKind.FUNCTION
        elif node_type in ("lambda", "lambda_expression"):
            scope_kind = NamespaceKind.LAMBDA
        elif node_type in ("list_comprehension", "dict_comprehension", "set_comprehension", "generator_expression"):
            scope_kind = NamespaceKind.COMPREHENSION

        if scope_kind:
            current_scope = ScopeDefinition(
                name=node_name if node_name != "anonymous" else f"<{scope_kind.value}>",
                kind=scope_kind,
                start_line=s_line,
                start_column=s_col,
                end_line=e_line,
                end_column=e_col,
                start_byte=s_byte,
                end_byte=e_byte,
                metadata={"python_node_type": node_type}
            )
            
            # Recurse children into current scope
            children_nodes = node_dict.get("children", []) or node_dict.get("body", []) or []
            if isinstance(children_nodes, list):
                for child in children_nodes:
                    self._walk_node(child, current_scope.children, parent_kind=scope_kind)
            
            out_scopes.append(current_scope)
        else:
            # Continue walking children at current scope level
            children_nodes = node_dict.get("children", []) or node_dict.get("body", []) or []
            if isinstance(children_nodes, list):
                for child in children_nodes:
                    self._walk_node(child, out_scopes, parent_kind=parent_kind)


class GenericFallbackScopeExtractor(AbstractScopeExtractor):
    """
    Fallback Scope Extractor for generic or unhandled languages.
    Extracts module level scope only.
    """

    def extract_scopes(self, parser_result: ParserResult) -> List[ScopeDefinition]:
        return []


class ScopeExtractorRegistry:
    """
    Registry for language-specific Scope Extractor plugins.
    """
    _extractors: Dict[Language, AbstractScopeExtractor] = {
        Language.PYTHON: PythonScopeExtractor()
    }

    @classmethod
    def register(cls, language: Language, extractor: AbstractScopeExtractor) -> None:
        cls._extractors[language] = extractor

    @classmethod
    def get_extractor(cls, language: Language) -> AbstractScopeExtractor:
        return cls._extractors.get(language, GenericFallbackScopeExtractor())
