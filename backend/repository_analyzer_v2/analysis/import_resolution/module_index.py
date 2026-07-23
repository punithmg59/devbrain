"""
analysis/import_resolution/module_index.py
-------------------------------------------
Phase 4.6 — Repository Module Index.

Provides O(1) repository-wide mapping between source file paths and fully qualified
module names (FQNs), computes relative import targets, and detects Python Standard
Library modules.

Design Principles
-----------------
- **O(1) Bidirectional Lookup**: Fast conversion between `file_path` and `module_fqn`.
- **Standard Library Detection**: Accurately classifies `sys.stdlib_module_names`.
- **Relative FQN Calculation**: Computes dot level (`.`, `..`, `...`) package bounds.
"""

from __future__ import annotations

import sys
from typing import Dict, Optional, Set


# Standard Library Modules Set (Python 3.10+ stdlib_module_names or comprehensive fallback)
STDLIB_MODULES: Set[str] = getattr(
    sys,
    "stdlib_module_names",
    {
        "abc", "argparse", "array", "ast", "asyncio", "base64", "bisect", "builtins",
        "collections", "concurrent", "contextlib", "copy", "csv", "dataclasses",
        "datetime", "decimal", "enum", "functools", "glob", "hashlib", "html",
        "http", "importlib", "inspect", "io", "itertools", "json", "logging",
        "math", "multiprocessing", "os", "pathlib", "pickle", "platform", "pprint",
        "random", "re", "shutil", "socket", "sqlite3", "string", "struct", "sys",
        "threading", "time", "traceback", "typing", "unittest", "urllib", "uuid",
        "weakref", "xml", "zipfile", "zlib",
    },
)


class ModuleIndex:
    """
    Repository-wide module index mapping file paths to module FQNs.

    Usage::

        index = ModuleIndex()
        index.register_file("app/services/user.py")
        fqn = index.get_module_fqn("app/services/user.py")  # -> 'app.services.user'
    """

    def __init__(self) -> None:
        self.file_path_to_fqn: Dict[str, str] = {}
        self.fqn_to_file_path: Dict[str, str] = {}

    def register_file(self, file_path: str, module_fqn: Optional[str] = None) -> str:
        """
        Register a file path and assign its module FQN.

        Parameters
        ----------
        file_path:
            Source file path (e.g. 'app/services/user.py').
        module_fqn:
            Optional explicit FQN. If omitted, computed automatically.

        Returns
        -------
        str
            Assigned module FQN.
        """
        norm_path = file_path.replace("\\", "/").strip("/")
        if not module_fqn:
            module_fqn = self.path_to_fqn(norm_path)

        self.file_path_to_fqn[norm_path] = module_fqn
        self.fqn_to_file_path[module_fqn] = norm_path
        return module_fqn

    def get_file_path(self, module_fqn: str) -> Optional[str]:
        """Return repository file path for a module FQN, or None."""
        return self.fqn_to_file_path.get(module_fqn)

    def get_module_fqn(self, file_path: str) -> Optional[str]:
        """Return module FQN for a repository file path, or None."""
        norm_path = file_path.replace("\\", "/").strip("/")
        return self.file_path_to_fqn.get(norm_path)

    def is_registered_module(self, module_fqn: str) -> bool:
        """Return True if `module_fqn` exists in repository index."""
        return module_fqn in self.fqn_to_file_path

    @staticmethod
    def is_stdlib_module(module_name: str) -> bool:
        """
        Check if `module_name` represents a Python Standard Library module.

        Parameters
        ----------
        module_name:
            Module string (e.g. 'os', 'json', 'urllib.parse').

        Returns
        -------
        bool
        """
        top_module = module_name.split(".")[0]
        return top_module in STDLIB_MODULES

    @staticmethod
    def path_to_fqn(file_path: str) -> str:
        """
        Convert file path to module FQN.

        Examples
        --------
        - 'app/services/user.py' -> 'app.services.user'
        - 'app/auth/__init__.py' -> 'app.auth'
        """
        norm = file_path.replace("\\", "/").strip("/")
        if norm.endswith(".py"):
            norm = norm[:-3]
        if norm.endswith("/__init__"):
            norm = norm[:-9]

        parts = [p for p in norm.split("/") if p]
        return ".".join(parts)

    def resolve_relative_import(
        self,
        source_module_fqn: str,
        relative_level: int,
        imported_module_part: Optional[str] = None,
    ) -> Optional[str]:
        """
        Compute target module FQN for a relative import.

        Parameters
        ----------
        source_module_fqn:
            FQN of source module where import is written (e.g. 'app.services.user').
        relative_level:
            Number of relative dots (1 for '.', 2 for '..', 3 for '...').
        imported_module_part:
            Target module suffix (e.g. 'service' in 'from .service import UserService').

        Returns
        -------
        Optional[str]
            Target module FQN, or None if relative level exceeds module depth.
        """
        if relative_level <= 0:
            return imported_module_part

        parts = source_module_fqn.split(".")

        # In Python:
        # from . import foo -> level 1 -> climbs to parent package of current module
        # from .. import foo -> level 2 -> climbs 2 levels
        if relative_level > len(parts):
            return None  # Climbed above top-level package

        base_parts = parts[:-relative_level]

        if imported_module_part:
            target_parts = base_parts + [imported_module_part]
        else:
            target_parts = base_parts

        return ".".join(target_parts) if target_parts else None

    def __len__(self) -> int:
        return len(self.fqn_to_file_path)
