"""
pipeline/workspace/exceptions.py
--------------------------------
Step 1 — Repository Analysis Pipeline Exceptions.

Production-grade error hierarchy for repository discovery, validation, loading,
and workspace construction.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class WorkspacePipelineError(Exception):
    """Base exception for all Repository Workspace Pipeline failures."""

    def __init__(
        self,
        message: str,
        code: str = "PIPELINE_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class RepositoryNotFoundError(WorkspacePipelineError):
    """Raised when target repository directory or URL cannot be found."""

    def __init__(self, path: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=f"Repository path or URL not found: '{path}'",
            code="REPO_NOT_FOUND",
            details={"path": path, **(details or {})},
        )


class PermissionDeniedError(WorkspacePipelineError):
    """Raised when process lacks read access to repository files."""

    def __init__(self, path: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=f"Permission denied accessing repository at '{path}'",
            code="PERMISSION_DENIED",
            details={"path": path, **(details or {})},
        )


class CloneFailureError(WorkspacePipelineError):
    """Raised when cloning remote Git repository fails."""

    def __init__(self, url: str, reason: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=f"Failed to clone repository '{url}': {reason}",
            code="CLONE_FAILURE",
            details={"url": url, "reason": reason, **(details or {})},
        )


class CorruptedRepositoryError(WorkspacePipelineError):
    """Raised when repository structure or Git tree is corrupted."""

    def __init__(self, path: str, reason: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=f"Repository at '{path}' is corrupted: {reason}",
            code="CORRUPTED_REPO",
            details={"path": path, "reason": reason, **(details or {})},
        )


class EmptyRepositoryError(WorkspacePipelineError):
    """Raised when target repository contains zero source files."""

    def __init__(self, path: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=f"Repository at '{path}' contains zero files or source code",
            code="EMPTY_REPO",
            details={"path": path, **(details or {})},
        )


class UnsupportedSourceError(WorkspacePipelineError):
    """Raised when source URL format or protocol is not supported."""

    def __init__(self, source: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=f"Unsupported repository source location: '{source}'",
            code="UNSUPPORTED_SOURCE",
            details={"source": source, **(details or {})},
        )


class PipelineTimeoutError(WorkspacePipelineError):
    """Raised when workspace scanning exceeds timeout threshold."""

    def __init__(self, timeout_sec: float, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=f"Repository scanning timed out after {timeout_sec:.2f} seconds",
            code="PIPELINE_TIMEOUT",
            details={"timeout_sec": timeout_sec, **(details or {})},
        )


class OperationCancelledError(WorkspacePipelineError):
    """Raised when repository scan is cancelled by user/caller."""

    def __init__(self, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message="Repository scanning operation was cancelled",
            code="OPERATION_CANCELLED",
            details=details or {},
        )
