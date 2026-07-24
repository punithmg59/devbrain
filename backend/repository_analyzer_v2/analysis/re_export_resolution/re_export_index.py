"""
analysis/re_export_resolution/re_export_index.py
-------------------------------------------------
Phase 4.7.1 — Re-Export Index Engine.

Provides O(1) hash-map lookups from (package_fqn, exported_name) to ExportRecord.
Also supports prefix-based package lookup and star-export expansion.

Design Principles
-----------------
- **O(1) Primary Lookup**: Direct dict access by (package_fqn, exported_name) key.
- **Star Export Tracking**: Maintains a separate star-export index per package.
- **Thread-Safe Reads**: Immutable after build; supports concurrent read access.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from models.re_export_models import ExportRecord


class ReExportIndex:
    """
    Fast multi-index lookup engine for repository package re-export records.

    Usage::

        index = ReExportIndex()
        index.build(export_records)

        rec = index.lookup("fastapi", "FastAPI")           # O(1) named lookup
        stars = index.get_star_exports("fastapi")          # wildcard expansions
        pkgs = index.get_packages_exporting("FastAPI")     # reverse lookup
    """

    def __init__(self) -> None:
        # Primary index: (package_fqn, exported_name) → ExportRecord
        self._named: Dict[Tuple[str, str], ExportRecord] = {}

        # Star exports per package: package_fqn → List[ExportRecord]
        self._stars: Dict[str, List[ExportRecord]] = {}

        # All exports per package: package_fqn → List[ExportRecord]
        self._by_package: Dict[str, List[ExportRecord]] = {}

        # Reverse lookup: exported_name → list of package FQNs
        self._by_name: Dict[str, List[str]] = {}

        # All records: export_id → ExportRecord
        self.records: Dict[str, ExportRecord] = {}

    def build(self, export_records: List[ExportRecord]) -> None:
        """
        Populate the index from a list of ExportRecord objects.

        Parameters
        ----------
        export_records:
            List of ExportRecord objects produced by ReExportBuilder.
        """
        for rec in export_records:
            self.records[rec.export_id] = rec
            self._by_package.setdefault(rec.package_fqn, []).append(rec)

            if rec.is_star_export:
                self._stars.setdefault(rec.package_fqn, []).append(rec)
            else:
                key = (rec.package_fqn, rec.exported_name)
                # Last-writer-wins for duplicates (validator will flag them)
                self._named[key] = rec
                self._by_name.setdefault(rec.exported_name, []).append(rec.package_fqn)

    def lookup(self, package_fqn: str, exported_name: str) -> Optional[ExportRecord]:
        """
        O(1) lookup of an ExportRecord by package FQN and exported name.

        Parameters
        ----------
        package_fqn:
            Package FQN (e.g. 'fastapi').
        exported_name:
            Name as seen by the importer (e.g. 'FastAPI').

        Returns
        -------
        Optional[ExportRecord]
            Matching ExportRecord, or None if not indexed.
        """
        return self._named.get((package_fqn, exported_name))

    def get_star_exports(self, package_fqn: str) -> List[ExportRecord]:
        """
        Return all star-export records for a package.

        Parameters
        ----------
        package_fqn:
            Package FQN (e.g. 'fastapi').

        Returns
        -------
        List[ExportRecord]
            Star export records; empty list if none declared.
        """
        return self._stars.get(package_fqn, [])

    def get_package_exports(self, package_fqn: str) -> List[ExportRecord]:
        """Return all ExportRecord objects for a package FQN."""
        return self._by_package.get(package_fqn, [])

    def get_packages_exporting(self, exported_name: str) -> List[str]:
        """Return all package FQNs that export a given name."""
        return self._by_name.get(exported_name, [])

    def has_package(self, package_fqn: str) -> bool:
        """Return True if the package has any re-export records."""
        return package_fqn in self._by_package

    def all_package_fqns(self) -> Set[str]:
        """Return the set of all indexed package FQNs."""
        return set(self._by_package.keys())

    def __len__(self) -> int:
        return len(self.records)
