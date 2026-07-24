"""
pipeline/workspace/models.py
----------------------------
Step 1 — Data Models for Repository Analysis Pipeline.

Defines Pydantic V2 native data contracts representing repository source locations,
technology/framework detection, required builder plugins, execution telemetry,
validation reports, and the final RepositoryWorkspace output.

CRITICAL INVARIANT:
-------------------
RepositoryWorkspace is strictly a pre-graph workspace manifest containing file lists,
metadata, and technology indicators. It MUST NOT contain AST nodes, Symbol Tables,
or Graph Edges.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from models.repository import RepositoryFile


class RepositorySource(str, Enum):
    """Origin source classification for repository access."""
    LOCAL_DIR = "local_dir"
    LOCAL_GIT = "local_git"
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    AZURE_DEVOPS = "azure_devops"


class RepositoryType(str, Enum):
    """Structural layout classification of repository."""
    SINGLE_PACKAGE = "single_package"
    MONOREPO = "monorepo"
    MULTI_MODULE = "multi_module"
    SCRIPT_ONLY = "script_only"
    UNKNOWN = "unknown"


class DetectedLanguage(BaseModel):
    """Programming language identified within repository."""
    name: str = Field(..., description="Language identifier name, e.g. 'python', 'typescript'")
    primary_extension: str = Field(..., description="Primary file extension, e.g. 'py', 'ts'")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Detection confidence score")
    file_count: int = Field(default=0, ge=0, description="Count of files identified for language")
    line_count: int = Field(default=0, ge=0, description="Estimated total lines of code")


class DetectedFramework(BaseModel):
    """Project framework or technology stack identified via manifests."""
    name: str = Field(..., description="Framework identifier, e.g. 'FastAPI', 'React', 'Next.js', 'Django'")
    manifest_file: str = Field(..., description="Manifest relative path where detected, e.g. 'pyproject.toml'")
    version: Optional[str] = Field(default=None, description="Framework version if parsed from manifest")


class PluginRequirement(BaseModel):
    """Specification of a Builder Plugin required for graph construction."""
    plugin_id: str = Field(..., description="Unique plugin ID, e.g. 'devbrain.plugin.python'")
    target_language: str = Field(..., description="Primary target language handled by plugin")
    framework: Optional[str] = Field(default=None, description="Specific framework extension if applicable")
    priority: int = Field(default=100, ge=0, description="Execution priority ordering")
    is_required: bool = Field(default=True, description="True if essential for pipeline graph building")


class RepositoryStatistics(BaseModel):
    """Aggregated filesystem and source code metrics."""
    total_files: int = Field(default=0, ge=0, description="Count of analyzable source files")
    total_bytes: int = Field(default=0, ge=0, description="Total size in bytes of analyzable source code")
    total_loc: int = Field(default=0, ge=0, description="Total lines of code across analyzable files")
    ignored_files_count: int = Field(default=0, ge=0, description="Total files excluded by ignore rules")
    ignored_bytes_count: int = Field(default=0, ge=0, description="Total bytes excluded by ignore rules")
    language_distribution: Dict[str, int] = Field(default_factory=dict, description="File count per language")
    extension_distribution: Dict[str, int] = Field(default_factory=dict, description="File count per extension")


class WorkspaceValidationIssue(BaseModel):
    """Individual issue recorded during repository validation."""
    severity: str = Field(..., description="'error' or 'warning'")
    code: str = Field(..., description="Diagnostic code, e.g. 'CORRUPTED_GIT_HEAD', 'READ_PERMISSION_DENIED'")
    message: str = Field(..., description="Human-readable issue description")
    file_path: Optional[str] = Field(default=None, description="Associated file relative path if applicable")


class WorkspaceValidationReport(BaseModel):
    """Pre-scan validation report evaluating repository integrity."""
    is_valid: bool = Field(default=True, description="True if no fatal validation errors exist")
    issues: List[WorkspaceValidationIssue] = Field(default_factory=list, description="List of recorded validation issues")
    error_count: int = Field(default=0, ge=0, description="Total error count")
    warning_count: int = Field(default=0, ge=0, description="Total warning count")


class RepositoryWorkspace(BaseModel):
    """
    Canonical output manifest produced by Step 1 Repository Analysis Pipeline.

    Holds all discovered analyzable files, detected technologies, required builder plugins,
    repository statistics, and validation diagnostics.
    """
    workspace_id: str = Field(
        default_factory=lambda: f"ws-{uuid.uuid4().hex[:12]}",
        description="Globally unique workspace manifest ID",
    )
    repository_name: str = Field(..., description="Derived repository name")
    repository_root: str = Field(..., description="Absolute filesystem root path of repository")
    source_type: RepositorySource = Field(default=RepositorySource.LOCAL_DIR, description="Repository access source type")
    repository_type: RepositoryType = Field(default=RepositoryType.SINGLE_PACKAGE, description="Layout structure classification")

    detected_languages: List[DetectedLanguage] = Field(default_factory=list, description="Detected programming languages")
    detected_frameworks: List[DetectedFramework] = Field(default_factory=list, description="Detected frameworks & manifests")
    builder_plugins_required: List[PluginRequirement] = Field(default_factory=list, description="Selected Builder Plugins required")

    statistics: RepositoryStatistics = Field(default_factory=RepositoryStatistics, description="Aggregate statistics")
    analyzable_files: List[RepositoryFile] = Field(default_factory=list, description="Ordered list of analyzable source files")

    ignored_files_count: int = Field(default=0, ge=0, description="Total ignored files count")
    ignored_directories_count: int = Field(default=0, ge=0, description="Total ignored directories count")

    warnings: List[str] = Field(default_factory=list, description="Recorded non-fatal pipeline warnings")
    validation_report: WorkspaceValidationReport = Field(default_factory=WorkspaceValidationReport, description="Validation report")
    pipeline_metadata: Dict[str, Any] = Field(default_factory=dict, description="Pipeline timing and execution metadata")
