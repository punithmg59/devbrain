import re


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
    r"@\w+\.(get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)


def parse_javascript(content: str, file_path: str) -> list[dict]:
    lines = content.splitlines()
    nodes: list[dict] = []
    imports = _JS_IMPORT.findall(content)
    exported = set(_JS_EXPORT.findall(content))

    def add_node(node_type: str, name: str, line_no: int, is_async: bool = False):
        full_path = f"{file_path}:{name}"
        nodes.append(
            {
                "node_type": node_type,
                "name": name,
                "full_path": full_path,
                "start_line": line_no,
                "end_line": line_no,
                "raw_code": lines[line_no - 1][:500] if line_no <= len(lines) else None,
                "signature": lines[line_no - 1].strip()[:1000] if line_no <= len(lines) else None,
                "calls": [],
                "imports": imports[:20],
                "is_exported": name in exported,
                "is_async": is_async,
                "http_method": None,
                "route_path": None,
            }
        )

    for match in _JS_FUNCTION.finditer(content):
        line_no = content[: match.start()].count("\n") + 1
        add_node("function", match.group(1), line_no, "async" in match.group(0))

    for match in _JS_ARROW.finditer(content):
        line_no = content[: match.start()].count("\n") + 1
        add_node("function", match.group(1), line_no, "async" in match.group(0))

    for match in _JS_CLASS.finditer(content):
        line_no = content[: match.start()].count("\n") + 1
        add_node("class", match.group(1), line_no)

    return nodes


def parse_python(content: str, file_path: str) -> list[dict]:
    import ast

    nodes: list[dict] = []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return nodes

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}" if module else alias.name)

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
            calls = [
                n.func.id
                for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            ][:30]
            http_method = None
            route_path = None
            for dec in node.decorator_list:
                dec_src = ast.get_source_segment(content, dec) or ""
                route_match = _FASTAPI_ROUTE.search(dec_src)
                if route_match:
                    http_method = route_match.group(1).upper()
                    route_path = route_match.group(2)
                    node_type = "api_route"

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
                    "imports": imports[:20],
                    "is_exported": not name.startswith("_") and not name.startswith("test_"),
                    "is_async": is_async,
                    "http_method": http_method,
                    "route_path": route_path,
                }
            )
            self.generic_visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ClassDef(self, node: ast.ClassDef):
            full_path = f"{file_path}:{node.name}"
            raw = ast.get_source_segment(content, node)
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
                    "imports": imports[:20],
                    "is_exported": not node.name.startswith("_"),
                    "is_async": False,
                    "http_method": None,
                    "route_path": None,
                }
            )
            self.class_stack.append(node.name)
            self.generic_visit(node)
            self.class_stack.pop()

    Visitor().visit(tree)
    return nodes


def parse_file(content: str, file_path: str) -> list[dict]:
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    if ext == "py":
        return parse_python(content, file_path)
    if ext in ("js", "jsx", "ts", "tsx"):
        return parse_javascript(content, file_path)
    return []
