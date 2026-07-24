"""
pipeline/workspace/loader.py
-----------------------------
Step 1 — Repository Loader Subsystem.

Opens local directories, local Git repositories, or clones remote GitHub repositories
into isolated local filesystem contexts. Designed with abstract handlers for future
GitLab, Bitbucket, and Azure DevOps extension.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import urllib.parse
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple

from pipeline.workspace.exceptions import (
    CloneFailureError,
    RepositoryNotFoundError,
    UnsupportedSourceError,
)
from pipeline.workspace.models import RepositorySource
from utils.logger import get_logger

logger = get_logger(__name__)


class LocalRepoContext:
    """Encapsulates a loaded repository context on local disk."""

    def __init__(
        self,
        repository_name: str,
        repository_root: str,
        source_type: RepositorySource,
        is_temporary: bool = False,
    ) -> None:
        self.repository_name = repository_name
        self.repository_root = repository_root
        self.source_type = source_type
        self.is_temporary = is_temporary

    def cleanup(self) -> None:
        """Remove temporary directory if created during remote clone."""
        if self.is_temporary and os.path.exists(self.repository_root):
            try:
                shutil.rmtree(self.repository_root, ignore_errors=True)
                logger.debug(f"[LocalRepoContext] Cleaned up temp repository at '{self.repository_root}'")
            except Exception as exc:
                logger.warning(f"[LocalRepoContext] Cleanup error: {exc}")


class IRepositorySourceHandler(ABC):
    """Abstract interface for repository source resolution and loading."""

    @abstractmethod
    def can_handle(self, source_location: str) -> bool:
        """Return True if handler supports the given source string."""
        pass

    @abstractmethod
    def load(self, source_location: str, destination_dir: Optional[str] = None) -> LocalRepoContext:
        """Load or clone repository into a local directory context."""
        pass


class LocalDirectoryHandler(IRepositorySourceHandler):
    """Handler for local directory and local Git repository paths."""

    def can_handle(self, source_location: str) -> bool:
        return os.path.exists(source_location) and os.path.isdir(source_location)

    def load(self, source_location: str, destination_dir: Optional[str] = None) -> LocalRepoContext:
        abs_path = os.path.abspath(source_location)
        repo_name = os.path.basename(abs_path.rstrip("/\\")) or "repository"
        is_git = os.path.exists(os.path.join(abs_path, ".git"))
        source_type = RepositorySource.LOCAL_GIT if is_git else RepositorySource.LOCAL_DIR

        logger.info(f"[LocalDirectoryHandler] Loaded local repository '{repo_name}' ({source_type.value}) at '{abs_path}'")
        return LocalRepoContext(
            repository_name=repo_name,
            repository_root=abs_path,
            source_type=source_type,
            is_temporary=False,
        )


class GitHubRepositoryHandler(IRepositorySourceHandler):
    """Handler for GitHub repository URLs (https://github.com/user/repo)."""

    def can_handle(self, source_location: str) -> bool:
        return "github.com" in source_location.lower()

    def load(self, source_location: str, destination_dir: Optional[str] = None) -> LocalRepoContext:
        url_clean = source_location.strip()
        parsed = urllib.parse.urlparse(url_clean)
        path_parts = [p for p in parsed.path.split("/") if p]

        if len(path_parts) < 2:
            raise UnsupportedSourceError(source_location, details={"reason": "Invalid GitHub repository URL path"})

        user, repo = path_parts[0], path_parts[1].replace(".git", "")

        target_dir = destination_dir or tempfile.mkdtemp(prefix=f"devbrain_repo_{repo}_")
        is_temp = destination_dir is None

        # Check git command availability
        if shutil.which("git"):
            cmd = f'git clone --depth 1 "{url_clean}" "{target_dir}"'
            ret = os.system(cmd)
            if ret != 0 or not os.path.exists(target_dir):
                if is_temp:
                    shutil.rmtree(target_dir, ignore_errors=True)
                raise CloneFailureError(url_clean, reason=f"git clone exited with code {ret}")
        else:
            raise CloneFailureError(url_clean, reason="Git executable not found on system PATH")

        logger.info(f"[GitHubRepositoryHandler] Cloned '{user}/{repo}' to '{target_dir}'")
        return LocalRepoContext(
            repository_name=repo,
            repository_root=target_dir,
            source_type=RepositorySource.GITHUB,
            is_temporary=is_temp,
        )


class RepositoryLoader:
    """
    Main loader orchestrator for opening local or remote repositories.

    Usage::

        loader = RepositoryLoader()
        context = loader.load("d:/devbrain/fastapi")
    """

    def __init__(self) -> None:
        self._handlers: List[IRepositorySourceHandler] = [
            LocalDirectoryHandler(),
            GitHubRepositoryHandler(),
        ]

    def register_handler(self, handler: IRepositorySourceHandler) -> None:
        """Register a custom repository source handler (e.g. GitLab, Bitbucket, Azure DevOps)."""
        self._handlers.insert(0, handler)

    def load(self, source_location: str, destination_dir: Optional[str] = None) -> LocalRepoContext:
        """
        Load or clone target repository location.
        """
        if not source_location or not source_location.strip():
            raise UnsupportedSourceError(source_location, details={"reason": "Source location cannot be empty"})

        for handler in self._handlers:
            if handler.can_handle(source_location):
                return handler.load(source_location, destination_dir=destination_dir)

        if not os.path.exists(source_location):
            raise RepositoryNotFoundError(source_location)

        raise UnsupportedSourceError(source_location)
