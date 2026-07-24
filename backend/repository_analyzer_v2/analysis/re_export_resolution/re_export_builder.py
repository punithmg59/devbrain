"""
analysis/re_export_resolution/re_export_builder.py
---------------------------------------------------
Phase 4.7.1 — Re-Export Pattern Scanner and ExportRecord Builder.

Scans all __init__.py `ExtractedModule` objects across a repository and produces
`ExportRecord` instances for every re-export pattern detected.

Supported Export Patterns
-------------------------
1.  from .module import Name              → FROM_IMPORT
2.  from .module import Name as Alias    → FROM_IMPORT_ALIAS
3.  from .module import *                → STAR_EXPORT
4.  from pkg.module import Name           → FROM_IMPORT (absolute intra-repo)
5.  __all__ = ["Name", ...]              → ALL_LIST
6.  __all__ += ["Name", ...]             → ALL_AUGMENTED
7.  __all__.append("Name")               → ALL_APPEND
8.  Multi-level chains resolved lazily by ReExportResolver

Design Principles
-----------------
- **No AST dependency**: Operates exclusively on `ExtractedModule` semantic objects.
- **Non-throwing**: Records errors without raising; validation is separate.
- **Idempotent**: Safe to call multiple times with the same inputs.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from models.re_export_models import ExportRecord, ExportType, ExportVisibility
from models.semantic import ExtractedImport, ExtractedModule, ExtractedVariable
from utils.logger import get_logger

if TYPE_CHECKING:
    from analysis.import_resolution.module_index import ModuleIndex


logger = get_logger(__name__)

# Regex for parsing string literals in __all__ assignments/augments
_STRING_LITERAL_RE = re.compile(r"""["']([^"']+)["']""")


class ReExportBuilder:
    """
    Scans __init__.py ExtractedModule objects and produces ExportRecord instances
    for every re-export pattern detected.

    Usage::

        builder = ReExportBuilder()
        records = builder.build_from_results(extraction_results, module_index)
    """

    def build_from_results(
        self,
        extraction_results: list,  # List[SemanticExtractionResult]
        module_index: ModuleIndex,
    ) -> List[ExportRecord]:
        """
        Scan all __init__.py files in extraction_results and build ExportRecord list.

        Parameters
        ----------
        extraction_results:
            List of SemanticExtractionResult objects covering the repository.
        module_index:
            Repository ModuleIndex for FQN resolution.

        Returns
        -------
        List[ExportRecord]
            All export records discovered in package __init__.py files.
        """
        all_records: List[ExportRecord] = []

        for res in extraction_results:
            if not self._is_init_file(res.file_path):
                continue

            try:
                records = self._build_from_module(res.module, module_index)
                all_records.extend(records)
                logger.debug(
                    "Re-export scan: %d exports found in %s",
                    len(records),
                    res.file_path,
                )
            except Exception as exc:
                logger.warning(
                    "Re-export scan failed for %s: %s",
                    res.file_path,
                    exc,
                )

        return all_records

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_init_file(file_path: str) -> bool:
        """Return True if the file path is a package __init__.py."""
        norm = file_path.replace("\\", "/")
        return norm.endswith("/__init__.py") or norm == "__init__.py"

    def _build_from_module(
        self,
        module: ExtractedModule,
        module_index: ModuleIndex,
    ) -> List[ExportRecord]:
        """Build all ExportRecord objects from a single __init__.py module."""
        records: List[ExportRecord] = []

        # Derive the package FQN from the module FQN
        # e.g. "fastapi.__init__" → "fastapi", "fastapi" → "fastapi"
        package_fqn = module.name
        if package_fqn.endswith(".__init__"):
            package_fqn = package_fqn[: -len(".__init__")]

        # 1. Scan import statements
        import_records = self._scan_imports(module, package_fqn, module_index)
        records.extend(import_records)

        # 2. Scan __all__ declarations in global_variables
        all_records = self._scan_all_declarations(module, package_fqn)
        records.extend(all_records)

        return records

    def _scan_imports(
        self,
        module: ExtractedModule,
        package_fqn: str,
        module_index: ModuleIndex,
    ) -> List[ExportRecord]:
        """Extract ExportRecord objects from the import statements in an __init__.py."""
        records: List[ExportRecord] = []

        for imp in module.imports:
            # Only from-import style produces re-exports in __init__.py
            if not imp.imported_names and not imp.is_relative:
                # Plain `import module` — not a re-export
                continue

            # Resolve the source module FQN
            source_module_fqn = self._resolve_source_module(
                imp, package_fqn, module_index
            )

            # Wildcard: from .module import *
            if "*" in imp.imported_names:
                rec = ExportRecord(
                    package_fqn=package_fqn,
                    package_file_path=module.file_path,
                    exported_name="*",
                    original_name="*",
                    alias=None,
                    source_module_fqn=source_module_fqn,
                    export_type=ExportType.STAR_EXPORT,
                    visibility=ExportVisibility.PUBLIC,
                    is_star_export=True,
                )
                records.append(rec)
                continue

            # Named from-imports
            for name in imp.imported_names:
                if not name or name == "*":
                    continue

                # Resolve alias
                alias: Optional[str] = None
                if isinstance(imp.aliases, dict):
                    alias = imp.aliases.get(name)
                elif isinstance(imp.aliases, list):
                    idx = imp.imported_names.index(name)
                    alias = imp.aliases[idx] if idx < len(imp.aliases) else None

                exported_name = alias if alias else name
                export_type = (
                    ExportType.FROM_IMPORT_ALIAS if alias else ExportType.FROM_IMPORT
                )
                visibility = (
                    ExportVisibility.PRIVATE
                    if exported_name.startswith("_")
                    else ExportVisibility.PUBLIC
                )

                rec = ExportRecord(
                    package_fqn=package_fqn,
                    package_file_path=module.file_path,
                    exported_name=exported_name,
                    original_name=name,
                    alias=alias,
                    source_module_fqn=source_module_fqn,
                    export_type=export_type,
                    visibility=visibility,
                    is_star_export=False,
                )
                records.append(rec)

        return records

    def _scan_all_declarations(
        self,
        module: ExtractedModule,
        package_fqn: str,
    ) -> List[ExportRecord]:
        """
        Extract ExportRecord objects from __all__ declarations.

        Handles:
        - __all__ = ["Name", "OtherName"]   → ALL_LIST
        - __all__ += ["Name"]               → ALL_AUGMENTED
        - __all__.append("Name")            → ALL_APPEND (via value_snippet)
        """
        records: List[ExportRecord] = []

        for var in module.global_variables:
            if var.name != "__all__":
                continue

            # Determine export type from value snippet
            snippet = var.value_snippet or ""
            export_type = self._classify_all_export_type(snippet)

            # Extract string literals from the value snippet
            names = _STRING_LITERAL_RE.findall(snippet)
            for name in names:
                if not name:
                    continue
                visibility = (
                    ExportVisibility.PRIVATE
                    if name.startswith("_")
                    else ExportVisibility.PUBLIC
                )
                rec = ExportRecord(
                    package_fqn=package_fqn,
                    package_file_path=module.file_path,
                    exported_name=name,
                    original_name=name,
                    alias=None,
                    source_module_fqn=None,  # Target resolved separately
                    export_type=export_type,
                    visibility=visibility,
                    is_star_export=False,
                )
                records.append(rec)

        return records

    @staticmethod
    def _classify_all_export_type(snippet: str) -> ExportType:
        """Determine the __all__ export pattern from a value snippet."""
        stripped = snippet.strip()
        if stripped.startswith("__all__ +=") or stripped.startswith("+="):
            return ExportType.ALL_AUGMENTED
        if "__all__.append" in stripped or stripped.startswith(".append"):
            return ExportType.ALL_APPEND
        return ExportType.ALL_LIST

    def _resolve_source_module(
        self,
        imp: ExtractedImport,
        package_fqn: str,
        module_index: ModuleIndex,
    ) -> Optional[str]:
        """
        Compute the FQN of the module from which names are imported.

        For relative imports (e.g. `from .applications import FastAPI`),
        we compute `package_fqn + "." + imported_module_part`.
        For absolute imports within the same repo, we use imp.module as-is.
        """
        if imp.is_relative or imp.relative_level > 0:
            # Relative import: module part appended to package FQN
            mod_part = imp.module  # e.g. "applications" in "from .applications import ..."
            if mod_part:
                return f"{package_fqn}.{mod_part}"
            else:
                # `from . import Name` — Name might itself be a sub-module
                return package_fqn
        else:
            # Absolute import
            return imp.module
