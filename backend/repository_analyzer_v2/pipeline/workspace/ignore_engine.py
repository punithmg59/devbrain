"""
pipeline/workspace/ignore_engine.py
-----------------------------------
Step 1 — Ignore Rule Engine & Binary File Detector.

Evaluates filesystem paths against built-in default ignore lists, custom user rules,
parsed `.gitignore` patterns, and binary content signatures.
"""

from __future__ import annotations

import fnmatch
import os
from typing import List, Optional, Set

from utils.logger import get_logger

logger = get_logger(__name__)

# Canonical list of directories to ignore by default across all codebases
DEFAULT_IGNORED_DIRS: Set[str] = {
    ".git",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "target",
    "coverage",
    ".next",
    ".nuxt",
    ".gradle",
    ".idea",
    ".vscode",
    "venv",
    ".venv",
    ".env",
    ".cache",
    "pytest_cache",
    ".pytest_cache",
    "out",
}

# Known binary and media extensions that are ignored by default
DEFAULT_BINARY_EXTENSIONS: Set[str] = {
    "pyc", "pyo", "pyd", "so", "dll", "dylib", "exe", "bin", "o", "a",
    "png", "jpg", "jpeg", "gif", "ico", "svg", "webp", "bmp", "tiff",
    "mp4", "mp3", "wav", "avi", "mov", "flv", "mkv",
    "zip", "tar", "gz", "bz2", "7z", "rar", "iso",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "db", "sqlite", "sqlite3", "class", "jar", "war", "ear",
    "woff", "woff2", "ttf", "eot", "otf",
}


class BinaryFileDetector:
    """Utility for detecting binary file signatures via magic bytes and null-byte inspection."""

    @staticmethod
    def is_binary_file(file_path: str, max_read_bytes: int = 8192) -> bool:
        """
        Return True if file is binary by checking for null bytes in the header.
        """
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            return False

        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        if ext in DEFAULT_BINARY_EXTENSIONS:
            return True

        try:
            with open(file_path, "rb") as f:
                chunk = f.read(max_read_bytes)
                if not chunk:
                    return False
                # Check for null bytes (characteristic of compiled/binary files)
                if b"\x00" in chunk:
                    return True
        except Exception:
            return True

        return False


class IgnoreRuleEngine:
    """
    Evaluates file and directory paths against ignore rules and gitignore patterns.

    Usage::

        engine = IgnoreRuleEngine.create_for_repository(repo_root)
        if engine.is_ignored(rel_path, is_dir=False):
            # Skip file
    """

    def __init__(
        self,
        ignored_dirs: Optional[Set[str]] = None,
        binary_exts: Optional[Set[str]] = None,
        custom_patterns: Optional[List[str]] = None,
        respect_gitignore: bool = True,
    ) -> None:
        self._ignored_dirs = set(ignored_dirs or DEFAULT_IGNORED_DIRS)
        self._binary_exts = set(binary_exts or DEFAULT_BINARY_EXTENSIONS)
        self._custom_patterns = list(custom_patterns or [])
        self._gitignore_patterns: List[str] = []
        self.respect_gitignore = respect_gitignore

    def add_gitignore_patterns(self, patterns: List[str]) -> None:
        """Append parsed `.gitignore` rule patterns."""
        for pat in patterns:
            cleaned = pat.strip()
            if cleaned and not cleaned.startswith("#"):
                self._gitignore_patterns.append(cleaned)

    def is_ignored_directory(self, dir_name: str, rel_path: str = "") -> bool:
        """Return True if directory name or path matches ignore rules."""
        if dir_name in self._ignored_dirs:
            return True
        if dir_name.startswith("."):
            return True

        # Match custom / gitignore rules
        path_to_check = rel_path or dir_name
        for pat in self._custom_patterns + self._gitignore_patterns:
            pat_clean = pat.rstrip("/")
            if fnmatch.fnmatch(path_to_check, pat_clean) or fnmatch.fnmatch(dir_name, pat_clean):
                return True

        return False

    def is_ignored_file(self, file_name: str, rel_path: str = "", abs_path: str = "") -> bool:
        """Return True if file is ignored by rules, extensions, gitignore, or binary signature."""
        if file_name.startswith("."):
            if file_name not in (".gitignore", ".env.example"):
                return True

        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        if ext in self._binary_exts:
            return True

        path_to_check = rel_path or file_name

        # Check custom rules and gitignore patterns
        for pat in self._custom_patterns + self._gitignore_patterns:
            if fnmatch.fnmatch(path_to_check, pat) or fnmatch.fnmatch(file_name, pat):
                return True

        # Inspect null bytes if absolute path is available
        if abs_path and os.path.exists(abs_path):
            if BinaryFileDetector.is_binary_file(abs_path):
                return True

        return False

    @classmethod
    def create_for_repository(
        cls,
        repo_root: str,
        custom_patterns: Optional[List[str]] = None,
        respect_gitignore: bool = True,
    ) -> IgnoreRuleEngine:
        """
        Construct IgnoreRuleEngine and parse root `.gitignore` if present.
        """
        engine = cls(custom_patterns=custom_patterns, respect_gitignore=respect_gitignore)

        if respect_gitignore:
            gitignore_path = os.path.join(repo_root, ".gitignore")
            if os.path.exists(gitignore_path) and os.path.isfile(gitignore_path):
                try:
                    with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                        engine.add_gitignore_patterns(f.readlines())
                    logger.debug(f"[IgnoreRuleEngine] Loaded root .gitignore from '{gitignore_path}'")
                except Exception as exc:
                    logger.warning(f"[IgnoreRuleEngine] Error reading .gitignore: {exc}")

        return engine
