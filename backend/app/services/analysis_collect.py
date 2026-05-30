"""CPU/file-heavy analysis work (runs in a thread pool)."""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

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

    for rel_path, parsed_list in parsed_by_file.items():
        for p in parsed_list:
            from_path = p["full_path"]
            if from_path not in path_to_node_paths:
                continue

            for call_name in p.get("calls", []):
                if len(payload.edges) >= MAX_EDGES:
                    break
                for target_path in name_to_paths.get(call_name, []):
                    if target_path == from_path:
                        continue
                    key = (from_path, target_path, "calls")
                    if key not in seen_edges:
                        seen_edges.add(key)
                        payload.edges.append(
                            {"from_path": from_path, "to_path": target_path, "edge_type": "calls"}
                        )

            for imp in p.get("imports", []):
                if len(payload.edges) >= MAX_EDGES:
                    break
                target_file = _resolve_import(imp, rel_path, all_paths)
                if not target_file:
                    continue
                targets = file_to_paths.get(target_file, [])
                if not targets:
                    continue
                target_path = targets[0]
                key = (from_path, target_path, "imports")
                if key not in seen_edges:
                    seen_edges.add(key)
                    payload.edges.append(
                        {"from_path": from_path, "to_path": target_path, "edge_type": "imports"}
                    )

    payload.total_files = len(payload.files)
    payload.total_functions = sum(
        1 for n in payload.nodes if n["node_type"] in ("function", "method", "api_route")
    )
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

    if import_path.startswith("."):
        base = Path(from_file).parent
        raw = (base / import_path).as_posix()
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
        for c in candidates:
            if c in all_files:
                return c
        for path in all_files:
            if path.replace("/", ".").startswith(import_path):
                return path

    return None
