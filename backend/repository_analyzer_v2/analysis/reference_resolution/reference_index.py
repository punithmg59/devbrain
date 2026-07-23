"""
analysis/reference_resolution/reference_index.py
----------------------------------------------
Phase 4.7 — Reference Multi-Index Engine.

Pre-calculates lookup indices over `ReferenceRecord` and `ReferenceResolution` objects to provide
microsecond O(1) queries by Symbol ID, file path, scope ID, and reference kind.

Design Principles
-----------------
- **O(1) Pre-Indexed Lookups**: Zero linear array scanning.
- **Thread-Safe Reads**: Supports high-concurrency multi-threaded queries.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from models.reference_models import (
    ReferenceKind,
    ReferenceRecord,
    ReferenceResolution,
)


class ReferenceIndex:
    """
    Fast multi-index lookup engine for repository identifier references.

    Usage::

        index = ReferenceIndex()
        index.add_reference(record, resolution)
        symbol_refs = index.find_references("sym-123")
    """

    def __init__(self) -> None:
        self.references: Dict[str, ReferenceRecord] = {}
        self.resolutions: Dict[str, ReferenceResolution] = {}

        # Lookup Indices
        self.by_symbol_id: Dict[str, List[str]] = {}
        self.by_file_path: Dict[str, List[str]] = {}
        self.by_scope_id: Dict[str, List[str]] = {}
        self.by_kind: Dict[str, List[str]] = {}

    def add_reference(
        self,
        record: ReferenceRecord,
        resolution: Optional[ReferenceResolution] = None,
    ) -> None:
        """Add a `ReferenceRecord` and optional `ReferenceResolution` to multi-index maps."""
        self.references[record.id] = record

        # Index by File Path
        self.by_file_path.setdefault(record.file_path, []).append(record.id)

        # Index by Scope ID
        self.by_scope_id.setdefault(record.scope_id, []).append(record.id)

        # Index by Kind
        self.by_kind.setdefault(record.kind.value, []).append(record.id)

        # Index by Target Symbol ID
        if record.symbol_id:
            ref_list = self.by_symbol_id.setdefault(record.symbol_id, [])
            if record.id not in ref_list:
                ref_list.append(record.id)

        if resolution:
            self.resolutions[record.id] = resolution
            if resolution.symbol_id:
                res_list = self.by_symbol_id.setdefault(resolution.symbol_id, [])
                if record.id not in res_list:
                    res_list.append(record.id)

    def get_reference(self, reference_id: str) -> Optional[ReferenceRecord]:
        """Return `ReferenceRecord` by ID."""
        return self.references.get(reference_id)

    def get_resolution(self, reference_id: str) -> Optional[ReferenceResolution]:
        """Return `ReferenceResolution` by ID."""
        return self.resolutions.get(reference_id)

    def find_references(self, symbol_id: str) -> List[ReferenceRecord]:
        """Return all reference records bound to `symbol_id`."""
        ids = self.by_symbol_id.get(symbol_id, [])
        return [self.references[r] for r in ids if r in self.references]

    def find_file_references(self, file_path: str) -> List[ReferenceRecord]:
        """Return all reference records originating in file_path."""
        norm_path = file_path.replace("\\", "/").strip("/")
        ids = self.by_file_path.get(norm_path, [])
        return [self.references[r] for r in ids if r in self.references]

    def find_scope_references(self, scope_id: str) -> List[ReferenceRecord]:
        """Return all reference records occurring inside scope_id."""
        ids = self.by_scope_id.get(scope_id, [])
        return [self.references[r] for r in ids if r in self.references]

    def find_references_by_kind(self, kind: ReferenceKind) -> List[ReferenceRecord]:
        """Return all reference records matching reference kind."""
        ids = self.by_kind.get(kind.value, [])
        return [self.references[r] for r in ids if r in self.references]

    def __len__(self) -> int:
        return len(self.references)
