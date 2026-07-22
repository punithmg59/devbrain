from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Language(str, Enum):
    """Supported programming languages for analysis."""
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    GO = "go"
    CSHARP = "csharp"
    UNKNOWN = "unknown"


class Folder(BaseModel):
    """Represents a folder in a repository."""
    path: str = Field(..., description="Relative path of the folder")
    name: str = Field(..., description="Name of the folder")


class RepositoryFile(BaseModel):
    """Represents a file in a repository with metadata for analysis."""
    path: str = Field(..., description="Relative path to the file")
    name: str = Field(..., description="Name of the file")
    extension: str = Field(..., description="File extension without leading dot")
    absolute_path: Optional[str] = Field(default=None, description="Absolute filesystem path")
    size_bytes: int = Field(default=0, ge=0, description="Size of the file in bytes")
    content: Optional[str] = Field(default=None, description="Raw file content if loaded")
    language: str = Field(default="unknown", description="Detected programming language")
    hash_sha256: Optional[str] = Field(default=None, description="SHA256 content hash for incremental analysis")
    last_modified: Optional[float] = Field(default=None, description="Last modified POSIX timestamp")
    encoding: Optional[str] = Field(default="utf-8", description="File text encoding")
    line_count: int = Field(default=0, ge=0, description="Total line count")
    status: str = Field(default="discovered", description="File status (discovered, unreadable, ignored, too_large)")

    @field_validator("extension")
    @classmethod
    def validate_extension(cls, v: str) -> str:
        if v.startswith("."):
            return v[1:]
        return v


class RepositorySummary(BaseModel):
    """Statistical summary of a discovered repository."""
    repository_root: str = Field(..., description="Absolute path of the repository root")
    total_files: int = Field(default=0, ge=0, description="Total files discovered")
    total_folders: int = Field(default=0, ge=0, description="Total folders discovered")
    language_distribution: Dict[str, int] = Field(default_factory=dict, description="File count per language")
    total_size_bytes: int = Field(default=0, ge=0, description="Aggregate repository size in bytes")
    largest_file: Optional[str] = Field(default=None, description="Relative path of the largest file")
    largest_file_size_bytes: int = Field(default=0, ge=0, description="Size of the largest file in bytes")
    is_git: bool = Field(default=False, description="True if a valid Git repository root")


class DiscoveryConfig(BaseModel):
    """Configuration options for repository discovery scanning."""
    follow_symlinks: bool = Field(default=False, description="Whether to follow symbolic links")
    max_depth: Optional[int] = Field(default=None, description="Maximum directory traversal depth")
    max_file_size_kb: int = Field(default=5000, ge=1, description="Maximum file size in KB to process")
    custom_ignore_patterns: List[str] = Field(default_factory=list, description="Custom ignore glob patterns")
    compute_hashes: bool = Field(default=True, description="Whether to compute SHA256 content hashes")
    max_workers: int = Field(default=16, ge=1, le=128, description="Max worker threads for concurrent metadata extraction")


class Repository(BaseModel):
    """Represents a source code repository."""
    id: str = Field(..., description="Unique identifier for the repository")
    url: str = Field(..., description="Git or source URL")
    name: str = Field(..., description="Repository name")
    branch: str = Field(default="main", description="Target branch for analysis")
    commit_hash: Optional[str] = Field(default=None, description="Specific commit hash analyzed")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the repository was registered",
    )
