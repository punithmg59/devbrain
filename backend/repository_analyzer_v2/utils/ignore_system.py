"""
utils/ignore_system.py
----------------------
Ignore pattern matching engine supporting built-in patterns, .gitignore,
.devbrainignore, and custom rules. Zero external dependencies.
"""

from fnmatch import fnmatch
from pathlib import Path
from typing import List, Optional, Union

DEFAULT_BUILTIN_IGNORES: List[str] = [
    # VCS & IDEs
    ".git",
    ".git/*",
    ".idea",
    ".vscode",
    ".DS_Store",
    # Dependencies & Build Outputs
    "node_modules",
    "node_modules/*",
    "dist",
    "dist/*",
    "build",
    "build/*",
    "target",
    "target/*",
    "coverage",
    "coverage/*",
    "venv",
    "venv/*",
    ".venv",
    ".venv/*",
    "__pycache__",
    "__pycache__/*",
    ".cache",
    ".cache/*",
    # Binaries & Compiled Objects
    "*.pyc",
    "*.pyo",
    "*.class",
    "*.o",
    "*.so",
    "*.dll",
    "*.exe",
    "*.bin",
    "*.tar",
    "*.gz",
    "*.zip",
]


class IgnoreSystem:
    """
    Evaluates whether files or directories should be ignored during scanning.
    Parses .gitignore, .devbrainignore, built-ins, and custom ignore rules.
    """

    def __init__(
        self,
        repo_root: Union[str, Path],
        custom_patterns: Optional[List[str]] = None,
        load_gitignore: bool = True,
        load_devbrainignore: bool = True,
    ) -> None:
        self.repo_root: Path = Path(repo_root).resolve()
        self.patterns: List[str] = list(DEFAULT_BUILTIN_IGNORES)

        if custom_patterns:
            self.patterns.extend(custom_patterns)

        if load_gitignore:
            self._load_ignore_file(self.repo_root / ".gitignore")

        if load_devbrainignore:
            self._load_ignore_file(self.repo_root / ".devbrainignore")

    def _load_ignore_file(self, ignore_file_path: Path) -> None:
        """Reads ignore patterns from a file if it exists."""
        if not ignore_file_path.is_file():
            return

        try:
            content = ignore_file_path.read_text(encoding="utf-8", errors="replace")
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    if line.startswith("/"):
                        line = line[1:]
                    self.patterns.append(line)
        except Exception:
            pass

    def should_ignore(self, path: Union[str, Path]) -> bool:
        """
        Check if a given path (absolute or relative to repo_root) should be ignored.

        :param path: Absolute or relative path to file/folder
        :return: True if path matches any ignore rule, False otherwise
        """
        p = Path(path)
        if p.is_absolute():
            try:
                rel_path = p.relative_to(self.repo_root)
            except ValueError:
                rel_path = p
        else:
            rel_path = p

        rel_str = rel_path.as_posix()
        parts = rel_path.parts

        for pattern in self.patterns:
            pattern_clean = pattern.rstrip("/")

            # Check direct part matches (e.g. "node_modules", ".git")
            if any(part == pattern_clean for part in parts):
                return True

            # Check fnmatch against full relative path
            if fnmatch(rel_str, pattern) or fnmatch(rel_str, pattern_clean):
                return True

            # Check fnmatch against individual path segments (e.g. "*.pyc")
            if any(fnmatch(part, pattern_clean) for part in parts):
                return True

        return False
