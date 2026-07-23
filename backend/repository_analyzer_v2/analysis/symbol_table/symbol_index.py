"""
analysis/symbol_table/symbol_index.py
--------------------------------------
Phase 4.4 — Symbol Multi-Index Lookup Engine.

Constructs fast O(1) dictionary indices over a `SymbolTable` for instant lookup
by Symbol ID, FQN, Simple Name, Kind, File Path, and Parent ID.

Design Principles
-----------------
- **O(1) Direct Lookup**: Pre-indexes all primary access paths into hash maps.
- **Thread-Safe**: Immutable after index construction; safe for multi-threaded readers.
- **Zero Scanning**: Avoids linear list iterations for query operations.
- **Microsecond Latency**: Built for high-frequency queries in downstream static analysis.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List, Optional, Set

from models.symbol import Symbol, SymbolKind, SymbolMetrics
from analysis.symbol_table.symbol_table import SymbolTable


class SymbolIndex:
    """
    Multi-index lookup engine for a `SymbolTable`.

    Constructs pre-populated hash maps for instant O(1) queries across multiple attributes.
    """

    def __init__(self, symbol_table: SymbolTable) -> None:
        """
        Build index maps from a `SymbolTable`.

        Parameters
        ----------
        symbol_table:
            The target `SymbolTable` to index.
        """
        self._table = symbol_table
        self._by_id: Dict[str, Symbol] = {}
        self._by_fqn: Dict[str, Symbol] = {}
        self._by_name: Dict[str, List[Symbol]] = defaultdict(list)
        self._by_kind: Dict[SymbolKind, List[Symbol]] = defaultdict(list)
        self._by_file: Dict[str, List[Symbol]] = defaultdict(list)
        self._by_parent: Dict[str, List[Symbol]] = defaultdict(list)

        self._build_index()

    def _build_index(self) -> None:
        """Populate internal index dictionaries."""
        for symbol in self._table.symbols.values():
            self._by_id[symbol.id] = symbol
            self._by_fqn[symbol.fqn] = symbol
            self._by_name[symbol.name].append(symbol)
            self._by_kind[symbol.kind].append(symbol)
            self._by_file[symbol.file_path].append(symbol)

            if symbol.parent_id:
                self._by_parent[symbol.parent_id].append(symbol)

    def get_by_id(self, symbol_id: str) -> Optional[Symbol]:
        """Lookup symbol by its unique ID in O(1) time."""
        return self._by_id.get(symbol_id)

    def get_by_fqn(self, fqn: str) -> Optional[Symbol]:
        """Lookup symbol by its Fully Qualified Name (FQN) in O(1) time."""
        return self._by_fqn.get(fqn)

    def get_by_name(self, name: str) -> List[Symbol]:
        """Return list of symbols matching the simple identifier name in O(1) time."""
        return self._by_name.get(name, [])

    def get_by_kind(self, kind: SymbolKind | str) -> List[Symbol]:
        """Return list of symbols matching the specified SymbolKind in O(1) time."""
        k = kind if isinstance(kind, SymbolKind) else SymbolKind(kind)
        return self._by_kind.get(k, [])

    def get_by_file(self, file_path: str) -> List[Symbol]:
        """Return list of symbols declared within a source file path in O(1) time."""
        return self._by_file.get(file_path, [])

    def get_by_parent(self, parent_id: str) -> List[Symbol]:
        """Return list of direct child symbols for a parent symbol ID in O(1) time."""
        return self._by_parent.get(parent_id, [])

    def get_children(self, symbol_id: str) -> List[Symbol]:
        """Alias for get_by_parent for symbol hierarchy traversal."""
        return self.get_by_parent(symbol_id)

    def search_by_name_prefix(self, prefix: str, limit: int = 50) -> List[Symbol]:
        """
        Find symbols whose simple name starts with prefix.

        Parameters
        ----------
        prefix:
            Case-sensitive prefix to match.
        limit:
            Maximum number of matching symbols to return.

        Returns
        -------
        List[Symbol]
        """
        results: List[Symbol] = []
        for name, syms in self._by_name.items():
            if name.startswith(prefix):
                results.extend(syms)
                if len(results) >= limit:
                    return results[:limit]
        return results[:limit]

    def measure_lookup_performance(self, iterations: int = 10000) -> float:
        """
        Measure average lookup latency in microseconds over N iterations.

        Returns
        -------
        float
            Average lookup latency per operation in microseconds.
        """
        if not self._by_id:
            return 0.0

        sample_ids = list(self._by_id.keys())
        sample_fqns = list(self._by_fqn.keys())

        num_samples = len(sample_ids)
        start = time.perf_counter()

        for i in range(iterations):
            sid = sample_ids[i % num_samples]
            sfqn = sample_fqns[i % num_samples]
            _ = self._by_id.get(sid)
            _ = self._by_fqn.get(sfqn)

        total_time_us = (time.perf_counter() - start) * 1_000_000.0
        return round(total_time_us / (iterations * 2), 3)

    @property
    def total_indexed(self) -> int:
        """Total number of indexed symbols."""
        return len(self._by_id)

    @property
    def total_files(self) -> int:
        """Total number of indexed source files."""
        return len(self._by_file)
