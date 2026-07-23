"""
analysis/import_resolution/import_index.py
-------------------------------------------
Phase 4.6 — Import Multi-Index Engine.

Pre-calculates lookup indices over `ImportRecord` and `ImportResolution` objects to provide
microsecond O(1) queries by file path, source module, target module, target symbol ID, and status.

Design Principles
-----------------
- **O(1) Pre-Indexed Lookups**: Zero linear array scanning.
- **Thread-Safe Reads**: Supports high-concurrency multi-threaded queries.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from models.import_models import (
    ImportRecord,
    ImportResolution,
    ImportResolutionStatus,
)


class ImportIndex:
    """
    Fast multi-index lookup engine for repository import records and resolutions.

    Usage::

        index = ImportIndex()
        index.add_import(record, resolution)
        file_imports = index.get_imports_by_file("app/auth.py")
    """

    def __init__(self) -> None:
        self.imports: Dict[str, ImportRecord] = {}
        self.resolutions: Dict[str, ImportResolution] = {}

        # Lookup Indices
        self.by_file_path: Dict[str, List[str]] = {}
        self.by_source_module: Dict[str, List[str]] = {}
        self.by_target_module: Dict[str, List[str]] = {}
        self.by_target_symbol_id: Dict[str, List[str]] = {}
        self.by_status: Dict[str, List[str]] = {}

    def add_import(
        self,
        record: ImportRecord,
        resolution: Optional[ImportResolution] = None,
    ) -> None:
        """Add an `ImportRecord` and optional `ImportResolution` to multi-index maps."""
        self.imports[record.id] = record

        # Index by File Path
        self.by_file_path.setdefault(record.source_file_path, []).append(record.id)

        # Index by Source Module
        self.by_source_module.setdefault(record.source_module_fqn, []).append(record.id)

        if resolution:
            self.resolutions[record.id] = resolution

            # Index by Target Module
            if resolution.target_module_fqn:
                self.by_target_module.setdefault(resolution.target_module_fqn, []).append(record.id)

            # Index by Target Symbol ID
            if resolution.target_symbol_id:
                self.by_target_symbol_id.setdefault(resolution.target_symbol_id, []).append(record.id)

            # Index by Status
            st = resolution.status.value
            self.by_status.setdefault(st, []).append(record.id)

    def get_import(self, import_id: str) -> Optional[ImportRecord]:
        """Return `ImportRecord` by ID."""
        return self.imports.get(import_id)

    def get_resolution(self, import_id: str) -> Optional[ImportResolution]:
        """Return `ImportResolution` by ID."""
        return self.resolutions.get(import_id)

    def get_imports_by_file(self, file_path: str) -> List[ImportRecord]:
        """Return all import records in source file."""
        norm_path = file_path.replace("\\", "/").strip("/")
        ids = self.by_file_path.get(norm_path, [])
        return [self.imports[i] for i in ids if i in self.imports]

    def get_imports_by_source_module(self, module_fqn: str) -> List[ImportRecord]:
        """Return all import records originating in source module FQN."""
        ids = self.by_source_module.get(module_fqn, [])
        return [self.imports[i] for i in ids if i in self.imports]

    def get_imports_by_target_module(self, module_fqn: str) -> List[ImportRecord]:
        """Return all import records pointing to target module FQN."""
        ids = self.by_target_module.get(module_fqn, [])
        return [self.imports[i] for i in ids if i in self.imports]

    def get_imports_by_target_symbol_id(self, symbol_id: str) -> List[ImportRecord]:
        """Return all import records resolved to target symbol ID."""
        ids = self.by_target_symbol_id.get(symbol_id, [])
        return [self.imports[i] for i in ids if i in self.imports]

    def get_imports_by_status(self, status: ImportResolutionStatus) -> List[ImportRecord]:
        """Return all import records matching resolution status."""
        ids = self.by_status.get(status.value, [])
        return [self.imports[i] for i in ids if i in self.imports]

    def __len__(self) -> int:
        return len(self.imports)
