import logging
import re

logger = logging.getLogger(__name__)


# --- JavaScript / TypeScript (regex-based) ---

_JS_FUNCTION = re.compile(
    r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)",
    re.MULTILINE,
)
_JS_ARROW = re.compile(
    r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(",
    re.MULTILINE,
)
_JS_CLASS = re.compile(r"^(?:export\s+)?class\s+(\w+)", re.MULTILINE)
_JS_IMPORT = re.compile(
    r"""import\s+(?:[\w*{}\s,]+\s+from\s+)?['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_JS_EXPORT = re.compile(
    r"^export\s+(?:default\s+)?(?:function|class|const)\s+(\w+)",
    re.MULTILINE,
)
_FASTAPI_ROUTE = re.compile(
    r"@?\w+\.(get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)


def parse_javascript(content: str, file_path: str) -> list[dict]:
    try:
        return _parse_javascript_impl(content, file_path)
    except Exception:
        logger.warning("JS/TS parser failed for %s; skipping file", file_path, exc_info=True)
        return []


def _parse_javascript_impl(content: str, file_path: str) -> list[dict]:
    # Regex fallback since no tree-sitter
    nodes: list[dict] = []
    seen_full_paths: set[str] = set()

    _CALL = re.compile(r"([\w]+)\s*\(")
    all_calls = list(set(m.group(1) for m in _CALL.finditer(content)))
    
    _JS_IMPORT = re.compile(r"""import\s+(?:[\w*{}\s,]+\s+from\s+)?['"]([^'"]+)['"]""", re.MULTILINE)
    all_imports = list(set(m.group(1) for m in _JS_IMPORT.finditer(content)))

    def _add_node(name: str, node_type: str, match: re.Match, is_async: bool = False) -> None:
        fp = f"{file_path}:{name}"
        if fp in seen_full_paths:
            return
        seen_full_paths.add(fp)
        nodes.append({
            "name": name,
            "node_type": node_type,
            "full_path": fp,
            "start_line": content[:match.start()].count("\n") + 1,
            "end_line": content[:match.start()].count("\n") + 1,
            "raw_code": content,
            "calls": all_calls,
            "imports": all_imports,
            "is_exported": "export" in match.group(0),
            "is_async": is_async or "async" in match.group(0),
            "http_method": None,
            "route_path": None
        })

    # functions (export const, function, etc)
    _FN = re.compile(r"(?:export\s+)?(?:default\s+)?(?:const|let|var)\s+([\w]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[\w]+)\s*=>", re.MULTILINE)
    for m in _FN.finditer(content):
        _add_node(m.group(1), "function", m)
        
    _FN2 = re.compile(r"(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([\w]+)\s*\(", re.MULTILINE)
    for m in _FN2.finditer(content):
        _add_node(m.group(1), "function", m)

    # classes
    _CLS = re.compile(r"(?:export\s+)?(?:default\s+)?class\s+([\w]+)", re.MULTILINE)
    for m in _CLS.finditer(content):
        _add_node(m.group(1), "class", m)

    return nodes


def parse_python(content: str, file_path: str) -> list[dict]:
    import ast

    nodes: list[dict] = []
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError, RecursionError) as exc:
        # ValueError covers source containing null bytes; RecursionError covers
        # pathologically nested source. None of these should fail the repo run.
        logger.debug("Python AST parse failed for %s: %s", file_path, exc)
        return nodes

    imports: list[str] = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
    except Exception:
        logger.debug("Import extraction failed for %s", file_path, exc_info=True)

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.class_stack: list[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
            is_async = isinstance(node, ast.AsyncFunctionDef)
            node_type = "method" if self.class_stack else "function"
            name = node.name
            if self.class_stack:
                name = f"{self.class_stack[-1]}.{node.name}"
            full_path = f"{file_path}:{name}"
            calls = []
            for n in ast.walk(node):
                if isinstance(n, ast.Call):
                    if isinstance(n.func, ast.Name):
                        calls.append(n.func.id)
                    elif isinstance(n.func, ast.Attribute):
                        calls.append(n.func.attr)
            http_method = None
            route_path = None
            for dec in node.decorator_list:
                dec_src = ast.get_source_segment(content, dec) or ""
                route_match = _FASTAPI_ROUTE.search(dec_src)
                if route_match:
                    http_method = route_match.group(1).upper()
                    route_path = route_match.group(2)
                    node_type = "api_route"

            # Extract Depends(...) from function default args
            depends_on: list[str] = []
            all_defaults = []
            # positional defaults are right-aligned to args
            all_defaults.extend(node.args.defaults)
            all_defaults.extend(node.args.kw_defaults)
            for default in all_defaults:
                if default is None:
                    continue
                if (
                    isinstance(default, ast.Call)
                    and isinstance(default.func, ast.Name)
                    and default.func.id == "Depends"
                    and default.args
                ):
                    dep_arg = default.args[0]
                    if isinstance(dep_arg, ast.Name):
                        depends_on.append(dep_arg.id)
                    elif isinstance(dep_arg, ast.Attribute):
                        depends_on.append(dep_arg.attr)

            raw = ast.get_source_segment(content, node)
            nodes.append(
                {
                    "node_type": node_type,
                    "name": name,
                    "full_path": full_path,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno or node.lineno,
                    "raw_code": (raw[:2000] if raw else None),
                    "signature": (raw.split("\n")[0][:1000] if raw else None),
                    "calls": list(dict.fromkeys(calls)),
                    "imports": imports,
                    "is_exported": not name.startswith("_") and not name.startswith("test_"),
                    "is_async": is_async,
                    "http_method": http_method,
                    "route_path": route_path,
                    "depends_on": depends_on,
                }
            )
            self.generic_visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ClassDef(self, node: ast.ClassDef):
            full_path = f"{file_path}:{node.name}"
            raw = ast.get_source_segment(content, node)

            # Extract base class names for inheritance edges
            bases: list[str] = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)

            nodes.append(
                {
                    "node_type": "class",
                    "name": node.name,
                    "full_path": full_path,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno or node.lineno,
                    "raw_code": (raw[:2000] if raw else None),
                    "signature": f"class {node.name}",
                    "calls": [],
                    "imports": imports,
                    "is_exported": not node.name.startswith("_"),
                    "is_async": False,
                    "http_method": None,
                    "route_path": None,
                    "bases": bases,
                }
            )
            self.class_stack.append(node.name)
            self.generic_visit(node)
            self.class_stack.pop()

    try:
        Visitor().visit(tree)
    except RecursionError:
        logger.warning("Python parser hit recursion limit on %s; returning partial nodes", file_path)
    except Exception:
        logger.warning("Python parser failed on %s; returning partial nodes", file_path, exc_info=True)
    return nodes


def parse_file(content: str, file_path: str) -> list[dict]:
    """Parse a single source file into node dicts.

    Contract: this function NEVER raises. Any failure for a single file returns an
    empty list so the repository-wide analysis can continue (fault tolerance).
    """
    try:
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        if ext == "py":
            return parse_python(content, file_path)
        if ext in ("js", "jsx", "ts", "tsx"):
            return parse_javascript(content, file_path)
        return []
    except Exception:
        logger.warning("Parser crashed on %s; skipping file", file_path, exc_info=True)
        return []
