"""
pipeline/workspace/analyzer.py
-------------------------------
Step 1 — Repository Analyzer Pipeline Coordinator.

Facade orchestrator for the Step 1 Repository Analysis Pipeline.
Executes repository opening/cloning, structural validation, ignore rule evaluation,
tree walking, technology detection, plugin selection, and builds `RepositoryWorkspace`.
"""

from __future__ import annotations

import time
from typing import List, Optional

from pipeline.workspace.directory_walker import DirectoryWalker
from pipeline.workspace.exceptions import WorkspacePipelineError
from pipeline.workspace.ignore_engine import IgnoreRuleEngine
from pipeline.workspace.language_detector import LanguageDetector
from pipeline.workspace.loader import RepositoryLoader
from pipeline.workspace.models import RepositoryWorkspace
from pipeline.workspace.plugin_selector import PluginSelector
from pipeline.workspace.validator import RepositoryValidator
from pipeline.workspace.workspace_builder import RepositoryWorkspaceBuilder
from utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryAnalyzer:
    """
    Main entry facade for executing Step 1 Repository Analysis Pipeline.

    Usage::

        analyzer = RepositoryAnalyzer()
        workspace = analyzer.analyze("d:/devbrain/fastapi")
    """

    def __init__(
        self,
        loader: Optional[RepositoryLoader] = None,
        validator: Optional[RepositoryValidator] = None,
        walker: Optional[DirectoryWalker] = None,
        language_detector: Optional[LanguageDetector] = None,
        plugin_selector: Optional[PluginSelector] = None,
        workspace_builder: Optional[RepositoryWorkspaceBuilder] = None,
    ) -> None:
        self.loader = loader or RepositoryLoader()
        self.validator = validator or RepositoryValidator()
        self.walker = walker or DirectoryWalker()
        self.language_detector = language_detector or LanguageDetector()
        self.plugin_selector = plugin_selector or PluginSelector()
        self.workspace_builder = workspace_builder or RepositoryWorkspaceBuilder()

    def analyze(
        self,
        source_location: str,
        destination_dir: Optional[str] = None,
        custom_ignore_patterns: Optional[List[str]] = None,
        respect_gitignore: bool = True,
        halt_on_validation_error: bool = False,
    ) -> RepositoryWorkspace:
        """
        Execute full Step 1 Repository Analysis Pipeline on target repository location.

        Parameters
        ----------
        source_location:
            Local directory path, local Git path, or remote GitHub URL.
        destination_dir:
            Optional target directory for cloning remote repository.
        custom_ignore_patterns:
            Optional list of custom glob patterns to ignore.
        respect_gitignore:
            True to parse and enforce root `.gitignore` rules (default True).
        halt_on_validation_error:
            True to raise `WorkspacePipelineError` if validation errors exist (default False).

        Returns
        -------
        RepositoryWorkspace
        """
        logger.info(f"[RepositoryAnalyzer] Starting repository workspace analysis for '{source_location}'")
        t_start = time.perf_counter()

        # 1. Open or Clone Repository
        context = self.loader.load(source_location, destination_dir=destination_dir)

        try:
            # 2. Validate Repository Structure & Permissions
            val_report = self.validator.validate(context.repository_root)
            if halt_on_validation_error and not val_report.is_valid:
                first_err = val_report.issues[0].message if val_report.issues else "Validation failed"
                raise WorkspacePipelineError(
                    message=f"Repository validation failed for '{context.repository_root}': {first_err}",
                    code="VALIDATION_FAILED",
                )

            # 3. Initialize Ignore Engine
            ignore_engine = IgnoreRuleEngine.create_for_repository(
                repo_root=context.repository_root,
                custom_patterns=custom_ignore_patterns,
                respect_gitignore=respect_gitignore,
            )

            # 4. Walk Directory Tree & Filter Files
            walk_result = self.walker.walk(context.repository_root, ignore_engine)

            # 5. Detect Languages & Framework Manifests
            languages, frameworks = self.language_detector.detect_technologies(
                context.repository_root,
                walk_result.analyzable_files,
            )

            # 6. Select Builder Plugin Requirements
            plugin_reqs = self.plugin_selector.select_plugins(languages, frameworks)

            dt_ms = (time.perf_counter() - t_start) * 1000.0

            # 7. Assemble RepositoryWorkspace Manifest
            workspace = self.workspace_builder.build(
                repo_context=context,
                walk_result=walk_result,
                detected_languages=languages,
                detected_frameworks=frameworks,
                plugin_requirements=plugin_reqs,
                validation_report=val_report,
                duration_ms=dt_ms,
            )

            logger.info(
                f"[RepositoryAnalyzer] Analysis completed for '{context.repository_name}': "
                f"Files={workspace.statistics.total_files:,}, LOC={workspace.statistics.total_loc:,}, "
                f"Duration={dt_ms:.2f}ms"
            )

            return workspace

        finally:
            # Clean up context if temporary directory was cloned
            if context.is_temporary:
                context.cleanup()
