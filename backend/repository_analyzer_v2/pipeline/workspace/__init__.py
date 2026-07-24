"""
pipeline/workspace/__init__.py
------------------------------
Step 1 — Repository Analysis Pipeline Package.

Public API re-exports for repository opening, validation, ignore rule evaluation,
tree walking, technology detection, builder plugin selection, and RepositoryWorkspace creation.
"""

from pipeline.workspace.exceptions import (
    CloneFailureError,
    CorruptedRepositoryError,
    EmptyRepositoryError,
    OperationCancelledError,
    PermissionDeniedError,
    PipelineTimeoutError,
    RepositoryNotFoundError,
    UnsupportedSourceError,
    WorkspacePipelineError,
)
from pipeline.workspace.models import (
    DetectedFramework,
    DetectedLanguage,
    PluginRequirement,
    RepositorySource,
    RepositoryStatistics,
    RepositoryType,
    RepositoryWorkspace,
    WorkspaceValidationIssue,
    WorkspaceValidationReport,
)
from pipeline.workspace.ignore_engine import BinaryFileDetector, IgnoreRuleEngine
from pipeline.workspace.validator import RepositoryValidator
from pipeline.workspace.loader import (
    GitHubRepositoryHandler,
    IRepositorySourceHandler,
    LocalDirectoryHandler,
    LocalRepoContext,
    RepositoryLoader,
)
from pipeline.workspace.directory_walker import DirectoryWalker, WalkResult
from pipeline.workspace.language_detector import LanguageDetector
from pipeline.workspace.plugin_selector import PluginSelector
from pipeline.workspace.workspace_builder import RepositoryWorkspaceBuilder
from pipeline.workspace.analyzer import RepositoryAnalyzer

__all__ = [
    # Facade & Main Subsystems
    "RepositoryAnalyzer",
    "RepositoryLoader",
    "RepositoryValidator",
    "DirectoryWalker",
    "LanguageDetector",
    "PluginSelector",
    "IgnoreRuleEngine",
    "BinaryFileDetector",
    "RepositoryWorkspaceBuilder",
    # Loader Context & Handlers
    "LocalRepoContext",
    "IRepositorySourceHandler",
    "LocalDirectoryHandler",
    "GitHubRepositoryHandler",
    "WalkResult",
    # Data Models & Enums
    "RepositorySource",
    "RepositoryType",
    "DetectedLanguage",
    "DetectedFramework",
    "PluginRequirement",
    "RepositoryStatistics",
    "WorkspaceValidationIssue",
    "WorkspaceValidationReport",
    "RepositoryWorkspace",
    # Exceptions
    "WorkspacePipelineError",
    "RepositoryNotFoundError",
    "PermissionDeniedError",
    "CloneFailureError",
    "CorruptedRepositoryError",
    "EmptyRepositoryError",
    "UnsupportedSourceError",
    "PipelineTimeoutError",
    "OperationCancelledError",
]
