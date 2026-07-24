"""
pipeline/workspace/workspace_builder.py
----------------------------------------
Step 1 — Repository Workspace Builder Engine.

Assembles workspace statistics, language breakdown, monorepo classification,
and produces the canonical `RepositoryWorkspace` manifest object.
"""

from __future__ import annotations

import time
from typing import List, Optional

from models.repository import RepositoryFile
from pipeline.workspace.loader import LocalRepoContext
from pipeline.workspace.models import (
    DetectedFramework,
    DetectedLanguage,
    PluginRequirement,
    RepositoryStatistics,
    RepositoryType,
    RepositoryWorkspace,
    WorkspaceValidationReport,
)
from pipeline.workspace.directory_walker import WalkResult
from utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryWorkspaceBuilder:
    """
    Builder engine for constructing the immutable RepositoryWorkspace manifest object.

    Usage::

        builder = RepositoryWorkspaceBuilder()
        workspace = builder.build(...)
    """

    def build(
        self,
        repo_context: LocalRepoContext,
        walk_result: WalkResult,
        detected_languages: List[DetectedLanguage],
        detected_frameworks: List[DetectedFramework],
        plugin_requirements: List[PluginRequirement],
        validation_report: WorkspaceValidationReport,
        duration_ms: float,
    ) -> RepositoryWorkspace:
        """
        Assemble all pipeline stage outcomes into a RepositoryWorkspace.
        """
        # 1. Compute Language and Extension Breakdown Maps
        lang_dist: Dict[str, int] = {}
        for lang in detected_languages:
            lang_dist[lang.name] = lang.file_count

        stats = RepositoryStatistics(
            total_files=len(walk_result.analyzable_files),
            total_bytes=walk_result.total_bytes,
            total_loc=walk_result.total_loc,
            ignored_files_count=walk_result.ignored_files_count,
            ignored_bytes_count=0,
            language_distribution=lang_dist,
            extension_distribution=walk_result.extension_distribution,
        )

        # 2. Classify Repository Layout Structure Type
        repo_type = self._classify_repository_type(
            walk_result.analyzable_files,
            detected_frameworks,
        )

        # 3. Assemble Metadata Metrics
        pipeline_metadata = {
            "execution_duration_ms": round(duration_ms, 2),
            "timestamp": time.time(),
            "analyzer_version": "2.5.0",
        }

        warnings_list: List[str] = [
            i.message for i in validation_report.issues if i.severity == "warning"
        ]

        logger.info(
            f"[RepositoryWorkspaceBuilder] Assembled RepositoryWorkspace for '{repo_context.repository_name}': "
            f"Files={stats.total_files:,}, LOC={stats.total_loc:,}, Languages={len(detected_languages)}, "
            f"Type={repo_type.value}, Duration={duration_ms:.2f}ms"
        )

        return RepositoryWorkspace(
            repository_name=repo_context.repository_name,
            repository_root=repo_context.repository_root,
            source_type=repo_context.source_type,
            repository_type=repo_type,
            detected_languages=detected_languages,
            detected_frameworks=detected_frameworks,
            builder_plugins_required=plugin_requirements,
            statistics=stats,
            analyzable_files=walk_result.analyzable_files,
            ignored_files_count=walk_result.ignored_files_count,
            ignored_directories_count=walk_result.ignored_directories_count,
            warnings=warnings_list,
            validation_report=validation_report,
            pipeline_metadata=pipeline_metadata,
        )

    @staticmethod
    def _classify_repository_type(
        files: List[RepositoryFile],
        frameworks: List[DetectedFramework],
    ) -> RepositoryType:
        """Classify repository structure (Monorepo, Single Package, Script Only)."""
        if not files:
            return RepositoryType.UNKNOWN

        total_loc = sum(f.line_count for f in files)
        if len(files) <= 3 and total_loc < 200:
            return RepositoryType.SCRIPT_ONLY

        # Check for multiple manifest instances (e.g. apps/web/package.json & packages/api/package.json)
        manifest_files = [fw.manifest_file for fw in frameworks if fw.manifest_file]
        distinct_dirs = {os.path.dirname(m) for m in manifest_files if os.path.dirname(m)}

        if len(distinct_dirs) >= 2:
            return RepositoryType.MONOREPO

        if len(manifest_files) >= 3:
            return RepositoryType.MULTI_MODULE

        return RepositoryType.SINGLE_PACKAGE
