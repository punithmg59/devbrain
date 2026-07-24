"""
analysis/function_call_detection/call_builder.py
-------------------------------------------------
Phase 4.7.2 — Function Call Extraction Builder Engine.

Traverses source file ASTs (`ASTRoot` / `ASTNode`) and semantic modules
(`ExtractedModule`) to extract every call invocation occurrence into
canonical `CallRecord` objects.

Design Principles
-----------------
- **Complete Call Expression Extraction**: Captures direct function calls, method
  calls, constructor calls, async calls, super calls, lambda calls, nested calls
  (e.g., `save(validate(user))`), and chained calls (e.g., `obj.login().token()`).
- **Enclosing Caller Scope Tracking**: Maintains a stack of enclosing function,
  method, class, and module symbols to bind `caller_symbol_id` and `caller_fqn`.
- **Non-Throwing AST Traversal**: Operates cleanly over AST trees without crashing
  on syntax recovery or partial parse nodes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from models.ast import ASTNode, ASTRoot, NodeRange, NodeType
from models.call_models import CallRecord, CallType
from models.semantic import ExtractedClass, ExtractedFunction, ExtractedModule, SemanticExtractionResult
from models.symbol import Symbol, SymbolKind
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.scope_resolution.scope_tree import ScopeTree
from analysis.function_call_detection.call_classifier import CallClassifier, CallClassificationResult
from utils.logger import get_logger

logger = get_logger(__name__)


class CallBuilder:
    """
    Call extraction engine that scans AST roots and semantic modules
    to discover all call invocation expressions.

    Usage::

        builder = CallBuilder(repository_id="repo1")
        records = builder.build_from_ast(ast_root, file_path, symbol_table, scope_tree)
    """

    def __init__(self, repository_id: str = "repo") -> None:
        self.repository_id = repository_id
        self._classifier = CallClassifier()

    def build_from_ast(
        self,
        ast_root: ASTRoot,
        file_path: str,
        symbol_table: SymbolTable,
        scope_tree: ScopeTree,
    ) -> List[CallRecord]:
        """
        Extract all `CallRecord` instances from an `ASTRoot` tree.

        Parameters
        ----------
        ast_root:
            DevBrain `ASTRoot` parse tree.
        file_path:
            Source file path relative to repository root.
        symbol_table:
            Repository `SymbolTable`.
        scope_tree:
            Lexical `ScopeTree`.

        Returns
        -------
        List[CallRecord]
        """
        records: List[CallRecord] = []
        caller_stack: List[Symbol] = []

        # Find top-level module symbol
        mod_symbols = [
            s for s in symbol_table.symbols.values()
            if s.file_path == file_path and s.kind == SymbolKind.MODULE
        ]
        top_caller = mod_symbols[0] if mod_symbols else None
        if top_caller:
            caller_stack.append(top_caller)

        self._traverse_ast(
            node=ast_root.root_node,
            file_path=file_path,
            symbol_table=symbol_table,
            scope_tree=scope_tree,
            caller_stack=caller_stack,
            records=records,
        )

        return records

    def build_from_module(
        self,
        module: ExtractedModule,
        symbol_table: SymbolTable,
        scope_tree: ScopeTree,
        ast_root: Optional[ASTRoot] = None,
    ) -> List[CallRecord]:
        """
        Extract `CallRecord` objects from an `ExtractedModule` (and optional `ASTRoot`).

        If `ast_root` is provided, full AST traversal is used; otherwise, semantic
        extraction structures (decorators, expressions, local variables) are scanned.
        """
        if ast_root:
            if isinstance(ast_root, dict):
                try:
                    ast_root = ASTRoot.model_validate(ast_root)
                except Exception as exc:
                    logger.debug("Failed to model_validate ast_root dict for %s: %s", module.file_path, exc)
                    ast_root = None
            if isinstance(ast_root, ASTRoot) and hasattr(ast_root, "root_node"):
                return self.build_from_ast(ast_root, module.file_path, symbol_table, scope_tree)

        # Fallback semantic scanner if AST root is omitted
        return self._scan_semantic_module(module, symbol_table, scope_tree)

    # ------------------------------------------------------------------
    # AST Traversal Logic
    # ------------------------------------------------------------------

    def _traverse_ast(
        self,
        node: ASTNode,
        file_path: str,
        symbol_table: SymbolTable,
        scope_tree: ScopeTree,
        caller_stack: List[Symbol],
        records: List[CallRecord],
    ) -> None:
        """Recursively walk `ASTNode` tree, tracking enclosing scope and capturing calls."""
        # 1. Update Caller Stack if node introduces a function/method/class
        pushed_symbol: Optional[Symbol] = None
        if node.type in (NodeType.FUNCTION, NodeType.METHOD, NodeType.CONSTRUCTOR, NodeType.CLASS):
            matching_sym = self._find_matching_symbol(node, file_path, symbol_table)
            if matching_sym:
                caller_stack.append(matching_sym)
                pushed_symbol = matching_sym

        # 2. Process CALL Node
        if node.type == NodeType.CALL:
            call_rec = self._extract_call_from_ast_node(
                node, file_path, caller_stack, symbol_table
            )
            if call_rec:
                records.append(call_rec)

        # 3. Recurse over Children
        for child in node.children:
            self._traverse_ast(
                node=child,
                file_path=file_path,
                symbol_table=symbol_table,
                scope_tree=scope_tree,
                caller_stack=caller_stack,
                records=records,
            )

        # Pop caller symbol if we pushed one
        if pushed_symbol and caller_stack and caller_stack[-1] == pushed_symbol:
            caller_stack.pop()

    def _extract_call_from_ast_node(
        self,
        call_node: ASTNode,
        file_path: str,
        caller_stack: List[Symbol],
        symbol_table: SymbolTable,
    ) -> Optional[CallRecord]:
        """Convert a `NodeType.CALL` ASTNode into a canonical `CallRecord`."""
        callee_expr, args, kwargs, is_async = self._parse_ast_call_components(call_node)
        if not callee_expr:
            callee_expr = call_node.name or call_node.value or "unknown"

        # Determine caller symbol
        current_caller = caller_stack[-1] if caller_stack else None
        caller_id = current_caller.id if current_caller else None
        caller_fqn = current_caller.fqn if current_caller else None

        # Classify Call
        classification = self._classifier.classify(
            callee_name=callee_expr,
            is_async=is_async,
            callee_symbol=None,  # Symbol binding performed in CallResolver stage
        )

        rng = call_node.range
        return CallRecord(
            repository_id=self.repository_id,
            caller_symbol_id=caller_id,
            caller_fqn=caller_fqn,
            callee_symbol_id=None,
            callee_fqn=None,
            callee_name=callee_expr,
            file_path=file_path,
            line=rng.start.line if rng else 1,
            column=rng.start.column if rng else 0,
            end_line=rng.end.line if rng else 1,
            end_column=rng.end.column if rng else 10,
            call_type=classification.call_type,
            is_async=classification.is_async,
            is_constructor=classification.is_constructor,
            is_method=classification.is_method,
            is_classmethod=classification.is_classmethod,
            is_staticmethod=classification.is_staticmethod,
            is_super_call=classification.is_super_call,
            is_lambda=classification.is_lambda,
            arguments=args,
            keyword_arguments=kwargs,
            range=rng,
        )

    def _parse_ast_call_components(
        self,
        call_node: ASTNode,
    ) -> Tuple[str, List[str], Dict[str, str], bool]:
        """
        Parse a `NodeType.CALL` AST node into (callee_expression, positional_args, kwargs, is_async).
        """
        callee_expr = call_node.name or ""
        args: List[str] = []
        kwargs: Dict[str, str] = {}
        is_async = "async" in call_node.metadata.modifiers or "await" in call_node.metadata.modifiers

        # Walk children to extract callee, positional args, and kwargs
        for child in call_node.children:
            if child.type in (NodeType.IDENTIFIER, NodeType.EXPRESSION, NodeType.PROPERTY) and not callee_expr:
                callee_expr = child.name or child.value or ""
            elif child.type == NodeType.PARAMETER:
                if child.name and child.value:
                    kwargs[child.name] = child.value
                elif child.value:
                    args.append(child.value)
                elif child.name:
                    args.append(child.name)
            elif child.type == NodeType.LITERAL and child.value:
                args.append(child.value)

        if not callee_expr and call_node.value:
            # Extract callee expression before '('
            val = call_node.value.strip()
            paren_idx = val.find("(")
            if paren_idx != -1:
                callee_expr = val[:paren_idx].strip()
            else:
                callee_expr = val

        return callee_expr, args, kwargs, is_async

    def _find_matching_symbol(
        self,
        node: ASTNode,
        file_path: str,
        symbol_table: SymbolTable,
    ) -> Optional[Symbol]:
        """Locate SymbolTable Symbol corresponding to an ASTNode definition."""
        if not node.name:
            return None

        for sym in symbol_table.symbols.values():
            if sym.file_path == file_path and sym.name == node.name:
                if sym.location and sym.location.range and node.range:
                    if sym.location.range.start.line == node.range.start.line:
                        return sym

        # Fallback by name match in file
        for sym in symbol_table.symbols.values():
            if sym.file_path == file_path and sym.name == node.name:
                return sym

        return None

    # ------------------------------------------------------------------
    # Fallback Semantic Module Scanner
    # ------------------------------------------------------------------

    def _scan_semantic_module(
        self,
        module: ExtractedModule,
        symbol_table: SymbolTable,
        scope_tree: ScopeTree,
    ) -> List[CallRecord]:
        """Scan ExtractedModule semantic structures when AST tree is unavailable."""
        records: List[CallRecord] = []
        file_path = module.file_path

        # Module caller
        mod_symbols = [
            s for s in symbol_table.symbols.values()
            if s.file_path == file_path and s.kind == SymbolKind.MODULE
        ]
        top_caller = mod_symbols[0] if mod_symbols else None

        # Scan Classes
        for cls in module.classes:
            cls_syms = [
                s for s in symbol_table.symbols.values()
                if s.file_path == file_path and s.name == cls.name and s.kind == SymbolKind.CLASS
            ]
            cls_caller = cls_syms[0] if cls_syms else top_caller

            # Base classes instantiation or decorator calls
            for dec in cls.decorators:
                if dec.arguments or "(" in dec.expression:
                    rec = self._make_call_record(
                        callee_expr=dec.name,
                        file_path=file_path,
                        caller_symbol=cls_caller,
                        args=dec.arguments,
                        rng=dec.range,
                    )
                    records.append(rec)

            for m in cls.methods:
                m_syms = [
                    s for s in symbol_table.symbols.values()
                    if s.file_path == file_path and s.name == m.name and s.kind in (SymbolKind.METHOD, SymbolKind.FUNCTION)
                ]
                m_caller = m_syms[0] if m_syms else cls_caller

                for dec in m.decorators:
                    if dec.arguments or "(" in dec.expression:
                        rec = self._make_call_record(
                            callee_expr=dec.name,
                            file_path=file_path,
                            caller_symbol=m_caller,
                            args=dec.arguments,
                            rng=dec.range,
                        )
                        records.append(rec)

                # Local variable value snippets in methods
                for var in m.local_variables:
                    if var.inferred_expression_kind == "call" and var.value_snippet:
                        callee_expr = self._extract_callee_from_snippet(var.value_snippet)
                        if callee_expr:
                            rec = self._make_call_record(
                                callee_expr=callee_expr,
                                file_path=file_path,
                                caller_symbol=m_caller,
                                rng=var.range,
                                is_async="await " in (var.value_snippet or ""),
                            )
                            records.append(rec)

        # Top-level Functions
        for fn in module.functions:
            fn_syms = [
                s for s in symbol_table.symbols.values()
                if s.file_path == file_path and s.name == fn.name and s.kind == SymbolKind.FUNCTION
            ]
            fn_caller = fn_syms[0] if fn_syms else top_caller

            for dec in fn.decorators:
                if dec.arguments or "(" in dec.expression:
                    rec = self._make_call_record(
                        callee_expr=dec.name,
                        file_path=file_path,
                        caller_symbol=fn_caller,
                        args=dec.arguments,
                        rng=dec.range,
                    )
                    records.append(rec)

            for var in fn.local_variables:
                if var.inferred_expression_kind == "call" and var.value_snippet:
                    callee_expr = self._extract_callee_from_snippet(var.value_snippet)
                    if callee_expr:
                        rec = self._make_call_record(
                            callee_expr=callee_expr,
                            file_path=file_path,
                            caller_symbol=fn_caller,
                            rng=var.range,
                            is_async="await " in (var.value_snippet or ""),
                        )
                        records.append(rec)

        return records

    def _make_call_record(
        self,
        callee_expr: str,
        file_path: str,
        caller_symbol: Optional[Symbol] = None,
        args: Optional[List[str]] = None,
        kwargs: Optional[Dict[str, str]] = None,
        rng: Optional[NodeRange] = None,
        is_async: bool = False,
    ) -> CallRecord:
        """Helper to build CallRecord from semantic components."""
        classification = self._classifier.classify(
            callee_name=callee_expr,
            is_async=is_async,
        )
        return CallRecord(
            repository_id=self.repository_id,
            caller_symbol_id=caller_symbol.id if caller_symbol else None,
            caller_fqn=caller_symbol.fqn if caller_symbol else None,
            callee_name=callee_expr,
            file_path=file_path,
            line=rng.start.line if rng else 1,
            column=rng.start.column if rng else 0,
            end_line=rng.end.line if rng else 1,
            end_column=rng.end.column if rng else 10,
            call_type=classification.call_type,
            is_async=classification.is_async,
            is_constructor=classification.is_constructor,
            is_method=classification.is_method,
            is_classmethod=classification.is_classmethod,
            is_staticmethod=classification.is_staticmethod,
            is_super_call=classification.is_super_call,
            is_lambda=classification.is_lambda,
            arguments=args or [],
            keyword_arguments=kwargs or {},
            range=rng,
        )

    @staticmethod
    def _extract_callee_from_snippet(snippet: str) -> Optional[str]:
        """Extract callee name expression from code snippet (e.g. 'user.login()' -> 'user.login')."""
        s = snippet.strip()
        if s.startswith("await "):
            s = s[6:].strip()
        paren_idx = s.find("(")
        if paren_idx != -1:
            return s[:paren_idx].strip()
        return s if s.isidentifier() else None
