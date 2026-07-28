"""
plugins/python/native_ast_converter.py
---------------------------------------
Fallback AST converter using Python's built-in `ast` module.
Converts Python standard library AST into DevBrain `ASTRoot` / `ASTNode` tree.
Used when Tree-sitter binary bindings are unavailable or restricted on host OS.
"""

from __future__ import annotations

import ast
import uuid
from typing import Any, List, Optional

from models.ast import ASTNode, ASTRoot, NodeLocation, NodeMetadata, NodeRange, NodeType
from utils.logger import get_logger

logger = get_logger(__name__)


def convert_python_native_ast(source_code: str, file_path: str) -> ASTRoot:
    """
    Parse Python source code using Python's built-in `ast` module and convert to `ASTRoot`.
    Recovers from syntax errors line-by-line / statement-by-statement.
    """
    lines = source_code.splitlines()
    total_lines = max(1, len(lines))

    root_range = NodeRange(
        start=NodeLocation(line=1, column=0),
        end=NodeLocation(line=total_lines, column=len(lines[-1]) if lines else 0),
    )

    docstring = None
    try:
        py_tree = ast.parse(source_code, filename=file_path)
        docstring = ast.get_docstring(py_tree)
        body_stmts = py_tree.body
    except SyntaxError:
        # Per-line/statement fallback recovery
        body_stmts = []
        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            try:
                sub_tree = ast.parse(line_str, filename=file_path)
                body_stmts.extend(sub_tree.body)
            except Exception:
                pass

    root_node = ASTNode(
        node_id=f"ast-{uuid.uuid4().hex[:12]}",
        type=NodeType.MODULE,
        name=file_path.split("/")[-1],
        range=root_range,
        metadata=NodeMetadata(
            docstring=docstring,
            is_definition=True,
        ),
    )

    visitor = NativeASTVisitor(file_path=file_path, lines=lines)
    visitor.visit_body(body_stmts, parent_node=root_node)

    ast_root = ASTRoot(
        root_id=f"tree-{uuid.uuid4().hex[:12]}",
        file_path=file_path,
        language="python",
        root_node=root_node,
    )
    ast_root.recalculate_metrics()
    return ast_root


class NativeASTVisitor:
    def __init__(self, file_path: str, lines: List[str]) -> None:
        self.file_path = file_path
        self.lines = lines

    def _make_range(self, node: ast.AST) -> NodeRange:
        start_line = getattr(node, "lineno", 1)
        start_col = getattr(node, "col_offset", 0)
        end_line = getattr(node, "end_lineno", start_line)
        end_col = getattr(node, "end_col_offset", start_col)

        start_line = max(1, start_line)
        end_line = max(start_line, end_line)
        start_col = max(0, start_col)
        end_col = max(0, end_col)

        return NodeRange(
            start=NodeLocation(line=start_line, column=start_col),
            end=NodeLocation(line=end_line, column=end_col),
        )

    def visit_body(self, body_nodes: List[ast.AST], parent_node: ASTNode) -> None:
        for stmt in body_nodes:
            self.visit_stmt(stmt, parent_node)

    def visit_stmt(self, stmt: ast.AST, parent: ASTNode) -> None:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.visit_function(stmt, parent)
        elif isinstance(stmt, ast.ClassDef):
            self.visit_class(stmt, parent)
        elif isinstance(stmt, ast.Import):
            self.visit_import(stmt, parent)
        elif isinstance(stmt, ast.ImportFrom):
            self.visit_import_from(stmt, parent)
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            self.visit_assign(stmt, parent)
        elif isinstance(stmt, ast.Return):
            ret_node = ASTNode(
                node_id=f"ast-{uuid.uuid4().hex[:12]}",
                type=NodeType.RETURN,
                range=self._make_range(stmt),
            )
            parent.add_child(ret_node)
            if stmt.value:
                self.visit_expr(stmt.value, ret_node)
        elif isinstance(stmt, ast.If):
            if_node = ASTNode(
                node_id=f"ast-{uuid.uuid4().hex[:12]}",
                type=NodeType.IF,
                range=self._make_range(stmt),
            )
            parent.add_child(if_node)
            self.visit_body(stmt.body, if_node)
            self.visit_body(stmt.orelse, if_node)
        elif isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
            loop_node = ASTNode(
                node_id=f"ast-{uuid.uuid4().hex[:12]}",
                type=NodeType.LOOP,
                range=self._make_range(stmt),
            )
            parent.add_child(loop_node)
            self.visit_body(stmt.body, loop_node)
            self.visit_body(stmt.orelse, loop_node)
        elif isinstance(stmt, ast.Try):
            try_node = ASTNode(
                node_id=f"ast-{uuid.uuid4().hex[:12]}",
                type=NodeType.TRY,
                range=self._make_range(stmt),
            )
            parent.add_child(try_node)
            self.visit_body(stmt.body, try_node)
            for handler in stmt.handlers:
                self.visit_body(handler.body, try_node)
            self.visit_body(stmt.finalbody, try_node)
            self.visit_body(stmt.orelse, try_node)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            with_node = ASTNode(
                node_id=f"ast-{uuid.uuid4().hex[:12]}",
                type=NodeType.STATEMENT,
                range=self._make_range(stmt),
            )
            parent.add_child(with_node)
            self.visit_body(stmt.body, with_node)
        elif isinstance(stmt, ast.Expr):
            self.visit_expr(stmt.value, parent)

    def visit_function(self, fn: ast.FunctionDef | ast.AsyncFunctionDef, parent: ASTNode) -> None:
        is_async = isinstance(fn, ast.AsyncFunctionDef)
        modifiers = []
        if is_async:
            modifiers.append("async")

        decorators = []
        for dec in fn.decorator_list:
            try:
                dec_str = ast.unparse(dec) if hasattr(ast, "unparse") else str(dec)
                decorators.append(f"@{dec_str}")
            except Exception:
                pass

        return_type = None
        if fn.returns:
            try:
                return_type = ast.unparse(fn.returns) if hasattr(ast, "unparse") else str(fn.returns)
            except Exception:
                pass

        docstring = ast.get_docstring(fn)

        fn_node = ASTNode(
            node_id=f"ast-{uuid.uuid4().hex[:12]}",
            type=NodeType.FUNCTION,
            name=fn.name,
            range=self._make_range(fn),
            metadata=NodeMetadata(
                docstring=docstring,
                modifiers=modifiers,
                decorators=decorators,
                type_annotation=return_type,
                is_definition=True,
            ),
        )

        # Detect parameters and default values
        all_pos_args = fn.args.posonlyargs + fn.args.args
        defaults = fn.args.defaults
        num_pos = len(all_pos_args)
        num_defaults = len(defaults)

        for i, arg in enumerate(all_pos_args):
            param_type = None
            if arg.annotation:
                try:
                    param_type = ast.unparse(arg.annotation) if hasattr(ast, "unparse") else str(arg.annotation)
                except Exception:
                    pass

            default_val = None
            default_idx = i - (num_pos - num_defaults)
            if default_idx >= 0:
                try:
                    default_val = ast.unparse(defaults[default_idx]) if hasattr(ast, "unparse") else str(defaults[default_idx])
                except Exception:
                    default_val = "..."

            param_node = ASTNode(
                node_id=f"ast-{uuid.uuid4().hex[:12]}",
                type=NodeType.PARAMETER,
                name=arg.arg,
                value=default_val,
                range=self._make_range(arg),
                metadata=NodeMetadata(
                    type_annotation=param_type,
                    is_definition=True,
                    custom={"has_default": default_val is not None},
                ),
            )
            fn_node.add_child(param_node)

        for i, arg in enumerate(fn.args.kwonlyargs):
            param_type = None
            if arg.annotation:
                try:
                    param_type = ast.unparse(arg.annotation) if hasattr(ast, "unparse") else str(arg.annotation)
                except Exception:
                    pass

            default_val = None
            if i < len(fn.args.kw_defaults) and fn.args.kw_defaults[i] is not None:
                try:
                    default_val = ast.unparse(fn.args.kw_defaults[i]) if hasattr(ast, "unparse") else str(fn.args.kw_defaults[i])
                except Exception:
                    default_val = "..."

            param_node = ASTNode(
                node_id=f"ast-{uuid.uuid4().hex[:12]}",
                type=NodeType.PARAMETER,
                name=arg.arg,
                value=default_val,
                range=self._make_range(arg),
                metadata=NodeMetadata(
                    type_annotation=param_type,
                    is_definition=True,
                    custom={"has_default": default_val is not None},
                ),
            )
            fn_node.add_child(param_node)

        if fn.args.vararg:
            fn_node.add_child(ASTNode(
                node_id=f"ast-{uuid.uuid4().hex[:12]}",
                type=NodeType.PARAMETER,
                name=f"*{fn.args.vararg.arg}",
                range=self._make_range(fn.args.vararg),
            ))
        if fn.args.kwarg:
            fn_node.add_child(ASTNode(
                node_id=f"ast-{uuid.uuid4().hex[:12]}",
                type=NodeType.PARAMETER,
                name=f"**{fn.args.kwarg.arg}",
                range=self._make_range(fn.args.kwarg),
            ))

        self.visit_body(fn.body, fn_node)

        # Check for yields in body
        for descendant in fn_node.walk():
            if descendant.type in (NodeType.EXPRESSION, NodeType.STATEMENT) and descendant.value == "yield":
                fn_node.metadata.custom["is_generator"] = True
                break

        parent.add_child(fn_node)

    def visit_class(self, cls_node: ast.ClassDef, parent: ASTNode) -> None:
        decorators = []
        for dec in cls_node.decorator_list:
            try:
                dec_str = ast.unparse(dec) if hasattr(ast, "unparse") else str(dec)
                decorators.append(f"@{dec_str}")
            except Exception:
                pass

        class_ast = ASTNode(
            node_id=f"ast-{uuid.uuid4().hex[:12]}",
            type=NodeType.CLASS,
            name=cls_node.name,
            range=self._make_range(cls_node),
            metadata=NodeMetadata(
                docstring=ast.get_docstring(cls_node),
                decorators=decorators,
                is_definition=True,
            ),
        )

        for base in cls_node.bases:
            base_name = getattr(base, "id", None) or (getattr(base, "attr", None) if isinstance(base, ast.Attribute) else None)
            if base_name:
                class_ast.add_child(ASTNode(
                    node_id=f"ast-{uuid.uuid4().hex[:12]}",
                    type=NodeType.IDENTIFIER,
                    name=base_name,
                    range=self._make_range(base),
                    metadata=NodeMetadata(is_reference=True),
                ))

        self.visit_body(cls_node.body, class_ast)
        parent.add_child(class_ast)

    def visit_import(self, imp: ast.Import, parent: ASTNode) -> None:
        imported_names = [alias.name for alias in imp.names]
        aliases = {alias.name: alias.asname for alias in imp.names if alias.asname}
        name = "import " + ", ".join(imported_names)
        parent.add_child(ASTNode(
            node_id=f"ast-{uuid.uuid4().hex[:12]}",
            type=NodeType.IMPORT,
            name=name,
            value=imported_names[0] if imported_names else "",
            range=self._make_range(imp),
            metadata=NodeMetadata(
                is_definition=False,
                custom={"imported_names": imported_names, "aliases": aliases},
            ),
        ))

    def visit_import_from(self, imp: ast.ImportFrom, parent: ASTNode) -> None:
        mod = "." * (imp.level or 0) + (imp.module or "")
        imported_names = [alias.name for alias in imp.names]
        aliases = {alias.name: alias.asname for alias in imp.names if alias.asname}
        name = f"from {mod} import " + ", ".join(imported_names)
        parent.add_child(ASTNode(
            node_id=f"ast-{uuid.uuid4().hex[:12]}",
            type=NodeType.IMPORT,
            name=name,
            value=mod,
            range=self._make_range(imp),
            metadata=NodeMetadata(
                is_definition=False,
                custom={"module": mod, "imported_names": imported_names, "aliases": aliases},
            ),
        ))

    def visit_assign(self, assign: ast.Assign | ast.AnnAssign, parent: ASTNode) -> None:
        targets = assign.targets if isinstance(assign, ast.Assign) else [assign.target]
        for tgt in targets:
            name = getattr(tgt, "id", None)
            if name:
                parent.add_child(ASTNode(
                    node_id=f"ast-{uuid.uuid4().hex[:12]}",
                    type=NodeType.ASSIGNMENT,
                    name=name,
                    range=self._make_range(assign),
                    metadata=NodeMetadata(is_definition=True),
                ))
            if hasattr(assign, "value") and assign.value:
                self.visit_expr(assign.value, parent)

    def visit_expr(self, expr: ast.AST, parent: ASTNode) -> None:
        if isinstance(expr, ast.Lambda):
            lambda_node = ASTNode(
                node_id=f"ast-{uuid.uuid4().hex[:12]}",
                type=NodeType.FUNCTION,
                name="<lambda>",
                range=self._make_range(expr),
                metadata=NodeMetadata(is_definition=True),
            )
            parent.add_child(lambda_node)
            self.visit_expr(expr.body, lambda_node)
        elif isinstance(expr, (ast.Yield, ast.YieldFrom)):
            yield_node = ASTNode(
                node_id=f"ast-{uuid.uuid4().hex[:12]}",
                type=NodeType.EXPRESSION,
                name="yield",
                value="yield",
                range=self._make_range(expr),
            )
            parent.add_child(yield_node)
        elif isinstance(expr, ast.Call):
            func_name = None
            if isinstance(expr.func, ast.Name):
                func_name = expr.func.id
            elif isinstance(expr.func, ast.Attribute):
                func_name = expr.func.attr

            if func_name:
                parent.add_child(ASTNode(
                    node_id=f"ast-{uuid.uuid4().hex[:12]}",
                    type=NodeType.CALL,
                    name=func_name,
                    range=self._make_range(expr),
                    metadata=NodeMetadata(is_reference=True),
                ))
            for arg in expr.args:
                self.visit_expr(arg, parent)
            for kw in expr.keywords:
                self.visit_expr(kw.value, parent)
