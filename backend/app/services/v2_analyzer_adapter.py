"""
app/services/v2_analyzer_adapter.py
------------------------------------
Production Adapter integrating Repository Analyzer V2 (`repository_analyzer_v2`)
with DevBrain's worker pipeline and PostgreSQL database.

This module replaces the legacy analyzer pipeline. All repository analysis operations
in DevBrain route exclusively through Repository Analyzer V2.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Ensure repository_analyzer_v2 is importable
backend_dir = Path(__file__).resolve().parent.parent.parent
v2_root = str(backend_dir / "repository_analyzer_v2")
if v2_root not in sys.path:
    sys.path.insert(0, v2_root)

from core.facade.facade import DependencyGraphFacade
from models.job import AnalysisJob as V2Job
from models.parser import (
    ParserError,
    ParserLanguage,
    ParserMetadata,
    ParserOptions,
    ParserResult,
    ParserStatistics,
    ParserStatus,
    ParserVersion,
)
from models.repository import DiscoveryConfig, RepositoryFile
from pipeline.discovery import RepositoryDiscovery
from plugins.python.python_parser_plugin import PythonParserPlugin

logger = logging.getLogger(__name__)


def _map_language(lang_str: str | None) -> ParserLanguage:
    if not lang_str:
        return ParserLanguage.UNKNOWN
    lang = lang_str.lower().strip()
    for item in ParserLanguage:
        if item.value == lang:
            return item
    if lang in ("py", "python"):
        return ParserLanguage.PYTHON
    if lang in ("js", "javascript"):
        return ParserLanguage.JAVASCRIPT
    if lang in ("ts", "typescript"):
        return ParserLanguage.TYPESCRIPT
    return ParserLanguage.UNKNOWN


class AnalysisPayloadV2:
    """Payload data container wrapping V2 analyzer output for DB persistence."""
    def __init__(self) -> None:
        self.files: List[dict] = []
        self.folders: List[dict] = []
        self.nodes: List[dict] = []
        self.edges: List[dict] = []
        self.total_files: int = 0
        self.total_functions: int = 0
        self.total_lines: int = 0
        self.failed_files: List[dict] = []
        self.binary_files_skipped: int = 0
        self.source_files_analyzed: int = 0


def run_v2_analysis_collection(clone_path: str, repository_id: str) -> AnalysisPayloadV2:
    """
    Execute Repository Analyzer V2 on `clone_path` and produce a populated `AnalysisPayloadV2`
    ready for database persistence.
    """
    logger.info(f"[V2Adapter] Starting Repository Analyzer V2 collection for '{repository_id}' at '{clone_path}'")
    payload = AnalysisPayloadV2()
    discovery = RepositoryDiscovery()

    # 1. Discover files and folders using V2 DiscoveryStage
    settings_max_size_kb = int(os.getenv("MAX_FILE_SIZE_KB", "5000"))
    config = DiscoveryConfig(max_file_size_kb=settings_max_size_kb)
    discovered_files: List[RepositoryFile] = discovery.discover(clone_path, config=config)
    summary = discovery.summarize(discovered_files, clone_path)

    payload.total_files = summary.total_files
    payload.total_lines = sum(f.line_count for f in discovered_files if f.status == "discovered")

    folder_file_counts: Dict[str, int] = {}

    for f in discovered_files:
        if f.status != "discovered":
            if f.status in ("unreadable", "too_large"):
                payload.failed_files.append({
                    "file_path": f.path,
                    "error_type": f.status,
                    "message": f"File status: {f.status}",
                })
            continue

        parent_folder = str(Path(f.path).parent).replace("\\", "/")
        if parent_folder == ".":
            parent_folder = ""
        folder_file_counts[parent_folder] = folder_file_counts.get(parent_folder, 0) + 1

        file_dict = {
            "file_path": f.path,
            "file_name": f.name,
            "extension": f".{f.extension}" if f.extension else None,
            "language": f.language,
            "folder_path": parent_folder,
            "depth": len(parent_folder.split("/")) if parent_folder else 0,
            "size_bytes": f.size_bytes,
            "line_count": f.line_count,
            "content_preview": None,
            "importance_score": 0.5,
        }

        # Read text preview safely
        try:
            full_p = Path(f.absolute_path)
            if full_p.exists():
                raw = full_p.read_bytes()
                if b"\x00" not in raw[:1024]:
                    text_content = raw.decode("utf-8", errors="replace")
                    file_dict["content_preview"] = text_content[:500] if text_content else None
        except Exception as exc:
            logger.debug(f"[V2Adapter] Could not read preview for {f.path}: {exc}")

        payload.files.append(file_dict)

    # Synthesize folder tree records
    all_folders: Set[str] = set(folder_file_counts.keys())
    for folder in list(all_folders):
        parts = folder.split("/") if folder else []
        for i in range(len(parts)):
            all_folders.add("/".join(parts[: i + 1]))
    all_folders.discard("")

    for folder_path in sorted(all_folders, key=lambda p: (len(p.split("/")), p)):
        parts = folder_path.split("/")
        payload.folders.append({
            "folder_path": folder_path,
            "folder_name": parts[-1],
            "parent_path": "/".join(parts[:-1]) if len(parts) > 1 else ("" if len(parts) == 1 else None),
            "depth": len(parts),
            "file_count": folder_file_counts.get(folder_path, 0),
            "function_count": 0,
        })

    # 2. Parse files using V2 Parser Plugins
    python_plugin = PythonParserPlugin()
    python_plugin.initialize()

    parser_results: List[ParserResult] = []

    for f in discovered_files:
        if f.status != "discovered":
            continue

        rel_path = f.path
        v2_job = V2Job(
            job_id=f"job-{abs(hash(rel_path))}",
            repository_id=repository_id,
            file=f,
            language=f.language,
        )

        lang_enum = _map_language(f.language)

        if lang_enum == ParserLanguage.PYTHON:
            try:
                res = python_plugin.parse(v2_job, context=None, options=ParserOptions())
                parser_results.append(res)
            except Exception as exc:
                logger.warning(f"[V2Adapter] Python parse failed for '{rel_path}': {exc}")
                res = ParserResult(
                    job_id=v2_job.job_id,
                    file_path=rel_path,
                    language=lang_enum,
                    status=ParserStatus.INTERNAL_ERROR,
                    errors=[ParserError(message=str(exc)[:500], severity="error")],
                    metadata=ParserMetadata(
                        parser_name="tree-sitter-python",
                        language=lang_enum,
                        version=ParserVersion(semver="1.0.0"),
                    ),
                    statistics=ParserStatistics(
                        lines_parsed=f.line_count or 0,
                        bytes_parsed=f.size_bytes or 0,
                    ),
                )
                parser_results.append(res)
        else:
            # Construct standard, schema-valid ParserResult for other languages
            res = ParserResult(
                job_id=v2_job.job_id,
                file_path=rel_path,
                language=lang_enum,
                status=ParserStatus.SUCCESS,
                metadata=ParserMetadata(
                    parser_name="v2_adapter_generic",
                    language=lang_enum,
                    version=ParserVersion(semver="1.0.0"),
                ),
                statistics=ParserStatistics(
                    lines_parsed=f.line_count or 0,
                    bytes_parsed=f.size_bytes or 0,
                ),
            )
            parser_results.append(res)

    payload.source_files_analyzed = len(parser_results)

    # 3. Extract nodes directly from parser raw_symbols (always available)
    func_count = 0
    existing_node_paths: Set[str] = set()
    seen_edge_keys: Set[Tuple[str, str, str]] = set()

    for pr in parser_results:
        for sym in (pr.raw_symbols or []):
            kind = sym.get("kind", "unknown")
            name = sym.get("name", "")
            fp = sym.get("file_path", pr.file_path)
            rng = sym.get("range") or {}
            start_info = rng.get("start", {}) if isinstance(rng, dict) else {}
            end_info = rng.get("end", {}) if isinstance(rng, dict) else {}

            s_line = start_info.get("line") if isinstance(start_info, dict) else None
            e_line = end_info.get("line") if isinstance(end_info, dict) else None

            full_path = f"{fp}::{name}" if name else fp

            if kind in ("function", "method", "api_route"):
                func_count += 1

            node_dict = {
                "node_type": kind,
                "name": name,
                "full_path": full_path,
                "start_line": s_line,
                "end_line": e_line,
                "file_path": fp,
                "raw_code": sym.get("docstring"),
                "signature": sym.get("signature", name),
                "calls": [],
                "imports": [],
                "is_exported": True,
                "is_async": False,
                "http_method": None,
                "route_path": None,
            }
            payload.nodes.append(node_dict)
            existing_node_paths.add(full_path)

            # contains edge: file -> symbol
            key = (fp, full_path, "contains")
            if key not in seen_edge_keys and fp != full_path:
                seen_edge_keys.add(key)
                payload.edges.append({
                    "from_path": fp,
                    "to_path": full_path,
                    "edge_type": "contains",
                })

        # Extract import edges from raw_imports
        for imp in (pr.raw_imports or []):
            mod = imp.get("module", "")
            names = imp.get("imported_names", [])
            source_fp = imp.get("file_path", pr.file_path)
            for iname in names:
                key = (source_fp, f"{mod}.{iname}" if mod else iname, "imports")
                if key not in seen_edge_keys:
                    seen_edge_keys.add(key)
                    payload.edges.append({
                        "from_path": source_fp,
                        "to_path": f"{mod}.{iname}" if mod else iname,
                        "edge_type": "imports",
                    })

    payload.total_functions = func_count

    # 4. Attempt DependencyGraphFacade pipeline for cross-file edges (call, inheritance, type-ref)
    try:
        analysis_result = DependencyGraphFacade.analyze_repository(
            parser_results=parser_results,
            repository_id=repository_id,
        )
        v2_graph = analysis_result.graph

        # Merge any additional symbols the pipeline discovered
        facade_symbols = DependencyGraphFacade.get_symbols(v2_graph)
        for sym in facade_symbols:
            node_kind = sym.kind.value if hasattr(sym.kind, "value") else str(sym.kind)
            sym_id = sym.id.value if hasattr(sym.id, "value") else str(sym.id)
            if sym_id not in existing_node_paths:
                start_line = (
                    sym.source_info.range.start.line
                    if (sym.source_info and getattr(sym.source_info, "range", None) and getattr(sym.source_info.range, "start", None))
                    else getattr(sym.source_info, "start_line", None)
                )
                end_line = (
                    sym.source_info.range.end.line
                    if (sym.source_info and getattr(sym.source_info, "range", None) and getattr(sym.source_info.range, "end", None))
                    else getattr(sym.source_info, "end_line", None)
                )
                payload.nodes.append({
                    "node_type": node_kind,
                    "name": sym.name,
                    "full_path": sym_id,
                    "start_line": start_line,
                    "end_line": end_line,
                    "file_path": sym.file_path,
                    "raw_code": sym.doc.detailed_description if sym.doc else None,
                    "signature": sym.fqn.value if hasattr(sym.fqn, "value") else str(sym.fqn),
                    "calls": [],
                    "imports": [],
                    "is_exported": True,
                    "is_async": False,
                    "http_method": None,
                    "route_path": None,
                })
                existing_node_paths.add(sym_id)

        # Merge cross-file edges from facade
        edge_type_map = {
            "call_edge": "calls",
            "import_edge": "imports",
            "inheritance_edge": "inherits",
            "type_reference_edge": "calls",
            "contains": "contains",
        }
        v2_edges = DependencyGraphFacade.get_edges(v2_graph)
        for e in v2_edges:
            from_p = e.source_symbol_id.value if hasattr(e.source_symbol_id, "value") else str(e.source_symbol_id)
            to_p = e.target_symbol_id.value if hasattr(e.target_symbol_id, "value") else str(e.target_symbol_id)
            raw_kind = e.kind.value if hasattr(e.kind, "value") else str(e.kind)
            etype = edge_type_map.get(raw_kind, raw_kind)
            key = (from_p, to_p, etype)
            if key not in seen_edge_keys:
                seen_edge_keys.add(key)
                payload.edges.append({
                    "from_path": from_p,
                    "to_path": to_p,
                    "edge_type": etype,
                })
    except Exception as exc:
        logger.warning(f"[V2Adapter] DependencyGraphFacade pipeline failed (non-fatal): {exc}")

    # 5. Synthesize File Nodes for DB tree views
    for file_dict in payload.files:
        fp = file_dict["file_path"]
        if fp not in existing_node_paths:
            payload.nodes.append({
                "node_type": "file",
                "name": file_dict["file_name"],
                "full_path": fp,
                "start_line": 1,
                "end_line": file_dict["line_count"],
                "file_path": fp,
                "raw_code": None,
                "signature": None,
                "calls": [],
                "imports": [],
                "is_exported": True,
                "is_async": False,
                "http_method": None,
                "route_path": None,
            })
            existing_node_paths.add(fp)

    logger.info(
        f"[V2Adapter] Repository Analyzer V2 run complete for '{repository_id}': "
        f"{payload.total_files} files, {len(payload.nodes)} nodes, {len(payload.edges)} edges extracted."
    )
    return payload

