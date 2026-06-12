"""CPU/file-heavy analysis work (runs in a thread pool)."""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

from app.services.code_parser import parse_file
from app.services.language_utils import (
    MAX_EDGES,
    detect_language,
    folder_depth,
    is_analyzable,
    iter_repo_files,
    normalize_folder_path,
)


@dataclass
class AnalysisPayload:
    files: list[dict] = field(default_factory=list)
    folders: list[dict] = field(default_factory=list)
    nodes: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)
    total_files: int = 0
    total_functions: int = 0
    total_lines: int = 0


def collect_analysis_payload(clone_path: str) -> AnalysisPayload:
    payload = AnalysisPayload()
    folder_file_counts: dict[str, int] = defaultdict(int)
    folder_function_counts: dict[str, int] = defaultdict(int)
    file_contents: dict[str, str] = {}
    all_paths: set[str] = set()
    parsed_by_file: dict[str, list[dict]] = {}

    for rel_path, full_path, size in iter_repo_files(clone_path):
        all_paths.add(rel_path)
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        file_contents[rel_path] = content
        line_count = content.count("\n") + (1 if content else 0)
        payload.total_lines += line_count

        folder = normalize_folder_path(str(Path(rel_path).parent))
        if folder == ".":
            folder = ""

        folder_file_counts[folder] += 1

        payload.files.append(
            {
                "file_path": rel_path,
                "file_name": Path(rel_path).name,
                "extension": Path(rel_path).suffix.lower() or None,
                "language": detect_language(rel_path),
                "folder_path": folder,
                "depth": folder_depth(folder),
                "size_bytes": size,
                "line_count": line_count,
                "content_preview": content[:500] if content else None,
                "importance_score": _importance_score(rel_path),
            }
        )

    for file_data in payload.files:
        rel_path = file_data["file_path"]
        if not is_analyzable(rel_path):
            continue
        content = file_contents.get(rel_path, "")
        parsed = parse_file(content, rel_path)
        parsed_by_file[rel_path] = parsed

        for p in parsed:
            if p["node_type"] in ("function", "method", "api_route"):
                folder_function_counts[file_data["folder_path"]] += 1
            payload.nodes.append({**p, "file_path": rel_path})

    all_folders: set[str] = set(folder_file_counts.keys())
    for folder in list(all_folders):
        parts = folder.split("/") if folder else []
        for i in range(len(parts)):
            all_folders.add("/".join(parts[: i + 1]))
    all_folders.discard("")

    for folder_path in sorted(all_folders, key=lambda p: (folder_depth(p), p)):
        parts = folder_path.split("/")
        payload.folders.append(
            {
                "folder_path": folder_path,
                "folder_name": parts[-1],
                "parent_path": "/".join(parts[:-1]) if len(parts) > 1 else ("" if len(parts) == 1 else None),
                "depth": folder_depth(folder_path),
                "file_count": folder_file_counts.get(folder_path, 0),
                "function_count": folder_function_counts.get(folder_path, 0),
            }
        )

    path_to_node_paths: dict[str, str] = {n["full_path"]: n["full_path"] for n in payload.nodes}
    name_to_paths: dict[str, list[str]] = defaultdict(list)
    file_to_paths: dict[str, list[str]] = defaultdict(list)

    for n in payload.nodes:
        file_to_paths[n["file_path"]].append(n["full_path"])
        short = n["name"].split(".")[-1]
        name_to_paths[short].append(n["full_path"])

    seen_edges: set[tuple[str, str, str]] = set()

    def _add_edge(from_p: str, to_p: str, etype: str) -> None:
        key = (from_p, to_p, etype)
        if key not in seen_edges and len(payload.edges) < MAX_EDGES:
            seen_edges.add(key)
            payload.edges.append({"from_path": from_p, "to_path": to_p, "edge_type": etype})

    # ── Regex patterns for Phase 7 (Database Intelligence) ──────────
    import re
    _RE_SELECT = re.compile(r"select\b.*?\bfrom\s+(\w+)", re.IGNORECASE | re.DOTALL)
    _RE_INSERT = re.compile(r"insert\s+into\s+(\w+)", re.IGNORECASE)
    _RE_UPDATE = re.compile(r"update\s+(\w+)\s+set", re.IGNORECASE)
    _RE_DELETE = re.compile(r"delete\s+from\s+(\w+)", re.IGNORECASE)

    # ORM model-to-table mapping (lowercase model -> table name)
    _ORM_TABLE = {
        "repo": "repos", "repofile": "repo_files", "node": "nodes",
        "edge": "edges", "foldertree": "folder_trees", "user": "users",
    }

    # Auth function names
    _AUTH_FUNCS = {"get_current_user", "verify_token", "require_admin", "get_current_active_user"}

    # Service keywords → service node names
    _SERVICE_PATTERNS: list[tuple[str, str]] = [
        ("groq(", "Groq"),
        ("groq_client", "Groq"),
        ("generate_node_summary", "Groq"),
        ("github(", "GitHub"),
        ("get_github_token", "GitHub"),
        ("clone_github_repo", "GitHub"),
        ("redis(", "Redis"),
        ("redis.", "Redis"),
        ("create_client(", "Supabase"),
        ("supabase.", "Supabase"),
        ("openai(", "OpenAI"),
    ]

    # External API domain → label
    _EXTERNAL_API_PATTERNS: list[tuple[str, str]] = [
        ("api.github.com", "GitHub API"),
        ("api.groq.com", "Groq API"),
        ("api.openai.com", "OpenAI API"),
        ("api.stripe.com", "Stripe API"),
        ("httpx.get", "External HTTP"),
        ("httpx.post", "External HTTP"),
        ("httpx.put", "External HTTP"),
        ("httpx.delete", "External HTTP"),
        ("httpx.patch", "External HTTP"),
        ("requests.get", "External HTTP"),
        ("requests.post", "External HTTP"),
        ("aiohttp.clientsession", "External HTTP"),
    ]

    # Middleware keywords
    _MIDDLEWARE_PATTERNS: list[tuple[str, str]] = [
        ("corsmiddleware", "CORSMiddleware"),
        ("authmiddleware", "AuthMiddleware"),
        ("loggingmiddleware", "LoggingMiddleware"),
        ("httpsredirectmiddleware", "HTTPSRedirectMiddleware"),
        ("trustedhostmiddleware", "TrustedHostMiddleware"),
        ("gzipmiddleware", "GZipMiddleware"),
    ]

    # Track generic nodes we need to create
    generic_nodes_needed: set[tuple[str, str]] = set()  # (node_type, name)

    # ═══════════════════════════════════════════════════════════
    # Main edge extraction loop
    # ═══════════════════════════════════════════════════════════
    for rel_path, parsed_list in parsed_by_file.items():
        for p in parsed_list:
            from_path = p["full_path"]
            if from_path not in path_to_node_paths:
                continue

            raw_lower = (p.get("raw_code") or "").lower()

            # ── Calls / API Calls ─────────────────────────────
            _IGNORE_CALLS = {"get", "post", "put", "delete", "patch", "append", "extend", "add", "commit", "execute", "query", "update", "pop", "remove", "keys", "values", "items"}
            for call_name in p.get("calls", []):
                if call_name in _IGNORE_CALLS:
                    continue
                for target_path in name_to_paths.get(call_name, []):
                    if target_path == from_path:
                        continue
                    etype = "api_calls" if p["node_type"] == "api_route" else "calls"
                    _add_edge(from_path, target_path, etype)

            # ── Imports ───────────────────────────────────────
            for imp in p.get("imports", []):
                target_file = _resolve_import(imp, rel_path, all_paths)
                if not target_file:
                    continue
                targets = file_to_paths.get(target_file, [])
                if targets:
                    _add_edge(from_path, targets[0], "imports")

            # ── Class contains method ─────────────────────────
            if p["node_type"] == "method" and "." in p["name"]:
                class_name = p["name"].split(".")[0]
                class_path = f"{rel_path}:{class_name}"
                _add_edge(class_path, from_path, "class_contains")

            # ── Phase 5: Inheritance ──────────────────────────
            if p["node_type"] == "class":
                for base_name in p.get("bases", []):
                    for target_path in name_to_paths.get(base_name, []):
                        _add_edge(from_path, target_path, "inherits")
                    # If base not in repo, create generic node
                    if base_name not in name_to_paths and base_name not in ("BaseModel", "object"):
                        generic_nodes_needed.add(("class", f"_ext_{base_name}"))
                        _add_edge(from_path, f"_ext_{base_name}", "inherits")

            # ── Phase 2 & 6: Auth Dependencies + Dependency Injection
            for dep_name in p.get("depends_on", []):
                if dep_name in _AUTH_FUNCS:
                    # Auth dependency
                    targets = name_to_paths.get(dep_name, [])
                    if targets:
                        _add_edge(from_path, targets[0], "auth_dependency")
                    else:
                        generic_nodes_needed.add(("function", f"_auth_{dep_name}"))
                        _add_edge(from_path, f"_auth_{dep_name}", "auth_dependency")
                else:
                    # Dependency injection
                    targets = name_to_paths.get(dep_name, [])
                    if targets:
                        _add_edge(from_path, targets[0], "dependency_injection")
                    else:
                        generic_nodes_needed.add(("function", f"_di_{dep_name}"))
                        _add_edge(from_path, f"_di_{dep_name}", "dependency_injection")

            # Skip body scanning for nodes with no raw_code
            if not raw_lower:
                continue

            # ── Phase 1: Service Dependencies ─────────────────
            for pattern, svc_name in _SERVICE_PATTERNS:
                if pattern in raw_lower:
                    generic_nodes_needed.add(("service", svc_name))
                    _add_edge(from_path, f"__svc__{svc_name}", "uses_service")

            # ── Phase 4: External APIs ────────────────────────
            for pattern, api_label in _EXTERNAL_API_PATTERNS:
                if pattern in raw_lower:
                    generic_nodes_needed.add(("external_api", api_label))
                    _add_edge(from_path, f"__api__{api_label}", "external_api")

            # ── Phase 3: Middleware ───────────────────────────
            if "add_middleware" in raw_lower or "middleware" in raw_lower:
                for pattern, mw_name in _MIDDLEWARE_PATTERNS:
                    if pattern in raw_lower:
                        generic_nodes_needed.add(("middleware", mw_name))
                        _add_edge(from_path, f"__mw__{mw_name}", "middleware_dependency")

            # ── Phase 7: Database Intelligence (fine-grained) ─
            # ORM-style: select(Model), Model.query, etc.
            for orm_key, table_name in _ORM_TABLE.items():
                # Patterns: select(Model), .where(Model., Model.id, etc.
                if orm_key in raw_lower:
                    generic_nodes_needed.add(("database_table", table_name))
                    tbl_path = "__table__" + table_name
                    # Determine operation type from surrounding context
                    select_pattern = "select(" + orm_key
                    if select_pattern in raw_lower:
                        _add_edge(from_path, tbl_path, "reads_table")
                    if "db.add" in raw_lower or "session.add" in raw_lower:
                        _add_edge(from_path, tbl_path, "writes_table")
                    if "update" in raw_lower and orm_key in raw_lower:
                        _add_edge(from_path, tbl_path, "updates_table")
                    delete_pattern = "delete(" + orm_key
                    if delete_pattern in raw_lower or "delete(" in raw_lower:
                        _add_edge(from_path, tbl_path, "deletes_table")

            # Raw SQL patterns
            for m in _RE_SELECT.finditer(raw_lower):
                tbl = m.group(1)
                if tbl not in ("select", "from", "where", "and", "or", "not"):
                    generic_nodes_needed.add(("database_table", tbl))
                    _add_edge(from_path, f"__table__{tbl}", "reads_table")
            for m in _RE_INSERT.finditer(raw_lower):
                tbl = m.group(1)
                generic_nodes_needed.add(("database_table", tbl))
                _add_edge(from_path, f"__table__{tbl}", "writes_table")
            for m in _RE_UPDATE.finditer(raw_lower):
                tbl = m.group(1)
                generic_nodes_needed.add(("database_table", tbl))
                _add_edge(from_path, f"__table__{tbl}", "updates_table")
            for m in _RE_DELETE.finditer(raw_lower):
                tbl = m.group(1)
                generic_nodes_needed.add(("database_table", tbl))
                _add_edge(from_path, f"__table__{tbl}", "deletes_table")

    # ═══════════════════════════════════════════════════════════
    # Compute totals before adding generic nodes
    # ═══════════════════════════════════════════════════════════
    payload.total_files = len(payload.files)
    payload.total_functions = sum(
        1 for n in payload.nodes if n["node_type"] in ("function", "method", "api_route")
    )

    # ── Add File nodes + contains edges ───────────────────────
    for file_data in payload.files:
        payload.nodes.append({
            "node_type": "file",
            "name": file_data["file_name"],
            "full_path": file_data["file_path"],
            "start_line": 1,
            "end_line": file_data["line_count"],
            "file_path": file_data["file_path"],
            "raw_code": None, "signature": None,
            "calls": [], "imports": [],
            "is_exported": True, "is_async": False,
            "http_method": None, "route_path": None,
        })
        fp = file_data["file_path"]
        for p in parsed_by_file.get(fp, []):
            if p["node_type"] in ("function", "class", "api_route", "method"):
                _add_edge(fp, p["full_path"], "contains")

    # ── Add generic nodes ─────────────────────────────────────
    def _make_generic(node_type: str, name: str, full_path: str) -> dict:
        return {
            "node_type": node_type, "name": name, "full_path": full_path,
            "start_line": None, "end_line": None, "file_path": None,
            "raw_code": None, "signature": None,
            "calls": [], "imports": [],
            "is_exported": False, "is_async": False,
            "http_method": None, "route_path": None,
        }

    for ntype, nname in generic_nodes_needed:
        if ntype == "service":
            payload.nodes.append(_make_generic("service", nname, f"__svc__{nname}"))
        elif ntype == "external_api":
            payload.nodes.append(_make_generic("external_api", nname, f"__api__{nname}"))
        elif ntype == "middleware":
            payload.nodes.append(_make_generic("middleware", nname, f"__mw__{nname}"))
        elif ntype == "database_table":
            payload.nodes.append(_make_generic("database_table", nname, f"__table__{nname}"))
        elif ntype == "class":
            payload.nodes.append(_make_generic("class", nname.replace("_ext_", ""), nname))
        elif ntype == "function":
            display_name = nname.replace("_auth_", "").replace("_di_", "")
            payload.nodes.append(_make_generic("function", display_name, nname))

    # ── Log results ───────────────────────────────────────────
    node_type_counts = defaultdict(int)
    for n in payload.nodes:
        node_type_counts[n["node_type"]] += 1
    edge_type_counts = defaultdict(int)
    for e in payload.edges:
        edge_type_counts[e["edge_type"]] += 1

    logger.info(f"Analysis collection complete for {clone_path}")
    logger.info(f"Total files: {payload.total_files}")
    logger.info(f"Total nodes extracted: {len(payload.nodes)}")
    logger.info(f"Node type breakdown: {dict(node_type_counts)}")
    logger.info(f"Total edges extracted: {len(payload.edges)}")
    logger.info(f"Edge type breakdown: {dict(edge_type_counts)}")

    return payload


def _importance_score(file_path: str) -> float:
    name = Path(file_path).name.lower()
    if name in ("main.py", "app.py", "index.js", "index.ts", "main.ts"):
        return 1.0
    if "router" in file_path or "route" in file_path or "api" in file_path:
        return 0.9
    if file_path.startswith("test") or "/test" in file_path:
        return 0.3
    return 0.5


def _resolve_import(import_path: str, from_file: str, all_files: set[str]) -> str | None:
    import_path = import_path.strip().rstrip("/")

    import os
    if import_path.startswith("."):
        base = Path(from_file).parent
        raw = os.path.normpath((base / import_path).as_posix()).replace("\\", "/")
        candidates = [
            raw,
            f"{raw}.ts",
            f"{raw}.tsx",
            f"{raw}.js",
            f"{raw}.jsx",
            f"{raw}/index.ts",
            f"{raw}/index.js",
        ]
        for c in candidates:
            if c in all_files:
                return c
        return None

    if "/" not in import_path and not import_path.startswith("@"):
        parts = import_path.replace(".", "/")
        candidates = [f"{parts}.py", f"{parts}/__init__.py"]
        
        # Try progressively shorter paths (for imports like app.models.Node where Node is not a file)
        parts_list = parts.split("/")
        while len(parts_list) > 0:
            sub_path = "/".join(parts_list)
            candidates.append(f"{sub_path}.py")
            candidates.append(f"{sub_path}/__init__.py")
            parts_list.pop()

        for c in candidates:
            if c in all_files:
                return c
        
        # Fallback partial match
        for path in all_files:
            if path.endswith(".py") and path.replace("/", ".").startswith(import_path):
                return path

    return None
