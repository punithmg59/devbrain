"""
pipeline/discovery.py
---------------------
Repository Discovery System module.

Transforms a target repository path into a validated collection of
RepositoryFile objects and generates a comprehensive RepositorySummary.

Features
--------
- Repository validation (path existence, read permissions, git/bare mode, empty repo detection)
- Recursive traversal respecting .gitignore, .devbrainignore, built-ins, and custom ignore rules
- Automatic programming language detection via LanguageDetector
- Concurrent file metadata extraction (size, line count, SHA256 hash, encoding, timestamp)
- Non-blocking error handling (unreadable, permission denied, or oversized files do not halt scan)
"""

from __future__ import annotations

import hashlib
import logging
import os
import pathlib
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Set, Tuple, Union

from config.settings import get_settings
from models.repository import (
    DiscoveryConfig,
    Folder,
    Language,
    RepositoryFile,
    RepositorySummary,
)
from pipeline.stage import PipelineContext, Stage
from utils.exceptions import ErrorCode, RepositoryError
from utils.ignore_system import IgnoreSystem
from utils.language_detector import LanguageDetector

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Repository Validator
# ---------------------------------------------------------------------------

class RepositoryValidator:
    """Validates repository paths, access permissions, git metadata, and empty states."""

    @classmethod
    def validate(cls, repo_path: Union[str, pathlib.Path]) -> Tuple[pathlib.Path, bool, bool]:
        """
        Validate repository path.

        :param repo_path: Directory path string or Path object
        :return: Tuple of (resolved_path, is_git_repository, is_empty)
        :raises RepositoryError: If path does not exist, is not a directory, or is unreadable.
        """
        path = pathlib.Path(repo_path).resolve()

        if not path.exists():
            raise RepositoryError(
                f"Repository path '{repo_path}' does not exist.",
                code=ErrorCode.REPO_NOT_FOUND,
                file_path=str(path),
            )

        if not path.is_dir():
            raise RepositoryError(
                f"Repository path '{repo_path}' is not a directory.",
                code=ErrorCode.REPO_NOT_FOUND,
                file_path=str(path),
            )

        if not os.access(path, os.R_OK):
            raise RepositoryError(
                f"Permission denied accessing repository path '{repo_path}'.",
                code=ErrorCode.REPO_ACCESS_DENIED,
                file_path=str(path),
            )

        is_git = (path / ".git").exists()

        # Check if empty (excluding hidden/VCS files)
        has_files = False
        try:
            for entry in path.iterdir():
                if entry.name not in (".git", ".idea", ".vscode"):
                    has_files = True
                    break
        except Exception as exc:
            raise RepositoryError(
                f"Error scanning repository directory '{repo_path}': {exc}",
                code=ErrorCode.REPO_ACCESS_DENIED,
                cause=exc,
            ) from exc

        is_empty = not has_files
        return path, is_git, is_empty


# ---------------------------------------------------------------------------
# File Metadata Extractor
# ---------------------------------------------------------------------------

def process_single_file(
    file_path: pathlib.Path,
    repo_root: pathlib.Path,
    max_file_size_kb: int = 5000,
    compute_hash: bool = True,
) -> RepositoryFile:
    """
    Extract metadata for a single file cleanly without raising exceptions on IO errors.

    :param file_path: Absolute Path to the file
    :param repo_root: Absolute Path to the repository root
    :param max_file_size_kb: Size limit in KB
    :param compute_hash: Whether to compute SHA256 digest
    :return: Populated RepositoryFile object
    """
    try:
        rel_path = file_path.relative_to(repo_root).as_posix()
    except ValueError:
        rel_path = file_path.as_posix()

    filename = file_path.name
    ext = file_path.suffix.lstrip(".")
    lang = LanguageDetector.detect(file_path).value

    # Check file status and stats
    try:
        stat = file_path.stat()
        size_bytes = stat.st_size
        mtime = stat.st_mtime
    except (OSError, PermissionError) as exc:
        logger.warning(f"[Discovery] Unreadable file '{rel_path}': {exc}")
        return RepositoryFile(
            path=rel_path,
            name=filename,
            extension=ext,
            absolute_path=str(file_path),
            language=lang,
            status="unreadable",
        )

    # Check file size limit
    if size_bytes > max_file_size_kb * 1024:
        logger.debug(f"[Discovery] Skipping large file '{rel_path}' ({size_bytes} bytes)")
        return RepositoryFile(
            path=rel_path,
            name=filename,
            extension=ext,
            absolute_path=str(file_path),
            size_bytes=size_bytes,
            language=lang,
            last_modified=mtime,
            status="too_large",
        )

    # Read content and compute hash/lines
    content_bytes = b""
    hash_sha256: Optional[str] = None
    line_count = 0
    encoding = "utf-8"

    try:
        content_bytes = file_path.read_bytes()
        if compute_hash:
            hash_sha256 = hashlib.sha256(content_bytes).hexdigest()

        try:
            text_content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            encoding = "latin-1"
            text_content = content_bytes.decode("latin-1", errors="replace")

        line_count = len(text_content.splitlines())
    except (OSError, PermissionError) as exc:
        logger.warning(f"[Discovery] Failed reading content for '{rel_path}': {exc}")
        return RepositoryFile(
            path=rel_path,
            name=filename,
            extension=ext,
            absolute_path=str(file_path),
            size_bytes=size_bytes,
            language=lang,
            last_modified=mtime,
            status="unreadable",
        )

    return RepositoryFile(
        path=rel_path,
        name=filename,
        extension=ext,
        absolute_path=str(file_path),
        size_bytes=size_bytes,
        language=lang,
        hash_sha256=hash_sha256,
        last_modified=mtime,
        encoding=encoding,
        line_count=line_count,
        status="discovered",
    )


# ---------------------------------------------------------------------------
# Main RepositoryDiscovery API
# ---------------------------------------------------------------------------

class RepositoryDiscovery:
    """
    Public discovery API service.
    Scans repositories, respects ignore rules, detects languages, and generates summaries.
    """

    def discover(
        self,
        repo_path: Union[str, pathlib.Path],
        config: Optional[DiscoveryConfig] = None,
    ) -> List[RepositoryFile]:
        """
        Traverse repository root recursively and return a list of RepositoryFile objects.

        :param repo_path: Path to repository on disk
        :param config: Optional DiscoveryConfig instance
        :return: List of validated RepositoryFile objects
        """
        cfg = config or DiscoveryConfig()
        root_path, is_git, is_empty = RepositoryValidator.validate(repo_path)

        if is_empty:
            logger.info(f"[Discovery] Repository at '{root_path}' is empty.")
            return []

        ignore_system = IgnoreSystem(
            repo_root=root_path,
            custom_patterns=cfg.custom_ignore_patterns,
        )

        candidate_files: List[pathlib.Path] = []
        visited_dirs: Set[pathlib.Path] = set()

        def crawl(dir_path: pathlib.Path, current_depth: int) -> None:
            if cfg.max_depth is not None and current_depth > cfg.max_depth:
                return

            try:
                resolved_dir = dir_path.resolve()
                if resolved_dir in visited_dirs and not cfg.follow_symlinks:
                    return
                visited_dirs.add(resolved_dir)

                for entry in dir_path.iterdir():
                    # Handle symlinks
                    if entry.is_symlink() and not cfg.follow_symlinks:
                        logger.debug(f"[Discovery] Skipping symlink '{entry}'")
                        continue

                    # Evaluate ignore rules
                    if ignore_system.should_ignore(entry):
                        continue

                    if entry.is_dir():
                        crawl(entry, current_depth + 1)
                    elif entry.is_file():
                        candidate_files.append(entry)
            except (OSError, PermissionError) as exc:
                logger.warning(f"[Discovery] Cannot access directory '{dir_path}': {exc}")

        crawl(root_path, current_depth=0)

        # Parallel extraction of file metadata
        discovered_files: List[RepositoryFile] = []
        if candidate_files:
            with ThreadPoolExecutor(max_workers=min(cfg.max_workers, len(candidate_files))) as executor:
                futures = [
                    executor.submit(
                        process_single_file,
                        f,
                        root_path,
                        cfg.max_file_size_kb,
                        cfg.compute_hashes,
                    )
                    for f in candidate_files
                ]
                for future in futures:
                    try:
                        res = future.result()
                        if res is not None:
                            discovered_files.append(res)
                    except Exception as exc:
                        logger.error(f"[Discovery] Metadata extraction thread error: {exc}")

        logger.info(
            f"[Discovery] Successfully scanned '{root_path}': "
            f"discovered {len(discovered_files)} file(s)."
        )
        return discovered_files

    def discover_file(
        self,
        file_path: Union[str, pathlib.Path],
        repo_root: Union[str, pathlib.Path],
        config: Optional[DiscoveryConfig] = None,
    ) -> Optional[RepositoryFile]:
        """
        Inspect and discover a single file within a repository context.

        :param file_path: Path to target file
        :param repo_root: Path to repository root
        :param config: Optional DiscoveryConfig
        :return: RepositoryFile object or None if ignored/missing
        """
        cfg = config or DiscoveryConfig()
        root_path = pathlib.Path(repo_root).resolve()
        f_path = pathlib.Path(file_path).resolve()

        if not f_path.exists() or not f_path.is_file():
            return None

        ignore_system = IgnoreSystem(
            repo_root=root_path,
            custom_patterns=cfg.custom_ignore_patterns,
        )

        if ignore_system.should_ignore(f_path):
            return None

        return process_single_file(f_path, root_path, cfg.max_file_size_kb, cfg.compute_hashes)

    def summarize(
        self,
        files: List[RepositoryFile],
        repo_root: Union[str, pathlib.Path],
    ) -> RepositorySummary:
        """
        Generate a statistical summary for a collection of discovered files.

        :param files: List of RepositoryFile objects
        :param repo_root: Repository root path
        :return: RepositorySummary object
        """
        root_path = pathlib.Path(repo_root).resolve()
        is_git = (root_path / ".git").exists()

        total_files = len(files)
        total_size_bytes = 0
        language_dist: Dict[str, int] = {}
        largest_file: Optional[str] = None
        largest_size = 0
        folders: Set[str] = set()

        for f in files:
            total_size_bytes += f.size_bytes
            language_dist[f.language] = language_dist.get(f.language, 0) + 1

            if f.size_bytes > largest_size:
                largest_size = f.size_bytes
                largest_file = f.path

            parent_folder = str(pathlib.Path(f.path).parent)
            if parent_folder != ".":
                folders.add(parent_folder)

        return RepositorySummary(
            repository_root=str(root_path),
            total_files=total_files,
            total_folders=len(folders),
            language_distribution=language_dist,
            total_size_bytes=total_size_bytes,
            largest_file=largest_file,
            largest_file_size_bytes=largest_size,
            is_git=is_git,
        )


# ---------------------------------------------------------------------------
# Pipeline Discovery Stage
# ---------------------------------------------------------------------------

class DiscoveryStage(Stage):
    """
    Stage 1 in the Repository Analyzer Pipeline.
    Executes RepositoryDiscovery and populates ctx.metadata with files and summary.
    """

    @property
    def name(self) -> str:
        return "Discovery"

    def setup(self, ctx: PipelineContext) -> None:
        logger.debug("[Discovery] Setup stage")

    def execute(self, ctx: PipelineContext) -> None:
        url_or_path = ctx.repository.url
        logger.info(f"[Discovery] Starting repository scan for '{url_or_path}'")

        # Handle remote URLs (e.g. http://, https://, git@) when not cloned locally
        if url_or_path.startswith(("http://", "https://", "git@")) and not pathlib.Path(url_or_path).exists():
            logger.warning(f"[Discovery] Remote repository URL '{url_or_path}' specified without local clone. Skipping filesystem walk.")
            ctx.metadata["discovered_files"] = []
            ctx.metadata["repository_summary"] = RepositorySummary(repository_root=url_or_path, is_git=True).model_dump()
            ctx.progress.total_files = 0
            return

        discovery = RepositoryDiscovery()
        settings = get_settings()

        config = DiscoveryConfig(
            max_file_size_kb=settings.max_file_size_kb,
            max_workers=settings.worker_count,
        )

        files = discovery.discover(url_or_path, config=config)
        summary = discovery.summarize(files, url_or_path)

        ctx.metadata["discovered_files"] = files
        ctx.metadata["repository_summary"] = summary.model_dump()
        ctx.progress.total_files = summary.total_files

        logger.info(
            f"[Discovery] Discovered {summary.total_files} file(s) across "
            f"{summary.total_folders} folder(s). Total size: {summary.total_size_bytes} bytes."
        )

    def teardown(self, ctx: PipelineContext) -> None:
        logger.debug("[Discovery] Teardown stage")
