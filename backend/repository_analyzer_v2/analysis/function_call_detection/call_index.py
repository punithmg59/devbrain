"""
analysis/function_call_detection/call_index.py
-----------------------------------------------
Phase 4.7.2 — Function Call Multi-Index Engine.

Pre-indexes `CallRecord` objects to support O(1) queries by call_id, caller_symbol_id,
callee_symbol_id, file_path, constructor calls, and call_type.

Design Principles
-----------------
- **O(1) Pre-Indexed Lookups**: Zero linear scanning overhead.
- **Thread-Safe Reads**: Supports high-concurrency queries.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from models.call_models import CallRecord, CallType


class CallIndex:
    """
    Fast multi-index lookup engine for repository call records.

    Usage::

        index = CallIndex()
        index.build(calls_list)
        caller_calls = index.find_calls_by_caller("sym-123")
        constructors = index.find_constructor_calls()
    """

    def __init__(self) -> None:
        self.calls: Dict[str, CallRecord] = {}

        # Lookup Indices
        self._by_caller: Dict[str, List[str]] = {}
        self._by_callee: Dict[str, List[str]] = {}
        self._by_file: Dict[str, List[str]] = {}
        self._by_type: Dict[str, List[str]] = {}
        self._constructors: List[str] = []

    def build(self, call_records: List[CallRecord]) -> None:
        """
        Populate the multi-index maps from a list of CallRecord objects.

        Parameters
        ----------
        call_records:
            List of CallRecord instances.
        """
        for call in call_records:
            self.add_call(call)

    def add_call(self, call: CallRecord) -> None:
        """Add a single `CallRecord` to index maps."""
        self.calls[call.call_id] = call

        # Caller Index
        if call.caller_symbol_id:
            self._by_caller.setdefault(call.caller_symbol_id, []).append(call.call_id)

        # Callee Index
        if call.callee_symbol_id:
            self._by_callee.setdefault(call.callee_symbol_id, []).append(call.call_id)

        # File Index
        norm_path = call.file_path.replace("\\", "/").strip("/")
        self._by_file.setdefault(norm_path, []).append(call.call_id)

        # Type Index
        type_str = call.call_type.value if isinstance(call.call_type, CallType) else str(call.call_type)
        self._by_type.setdefault(type_str, []).append(call.call_id)

        # Constructor Index
        if call.is_constructor or call.call_type == CallType.CONSTRUCTOR:
            self._constructors.append(call.call_id)

    def find_call(self, call_id: str) -> Optional[CallRecord]:
        """O(1) lookup of a CallRecord by ID."""
        return self.calls.get(call_id)

    def find_calls_by_caller(self, symbol_id: str) -> List[CallRecord]:
        """Return all CallRecord objects originated by a caller Symbol ID."""
        ids = self._by_caller.get(symbol_id, [])
        return [self.calls[c] for c in ids if c in self.calls]

    def find_calls_by_callee(self, symbol_id: str) -> List[CallRecord]:
        """Return all CallRecord objects targeting a callee Symbol ID."""
        ids = self._by_callee.get(symbol_id, [])
        return [self.calls[c] for c in ids if c in self.calls]

    def find_calls_in_file(self, file_path: str) -> List[CallRecord]:
        """Return all CallRecord objects in a source file."""
        norm_path = file_path.replace("\\", "/").strip("/")
        ids = self._by_file.get(norm_path, [])
        return [self.calls[c] for c in ids if c in self.calls]

    def find_constructor_calls(self) -> List[CallRecord]:
        """Return all constructor CallRecord objects."""
        return [self.calls[c] for c in self._constructors if c in self.calls]

    def find_calls_by_type(self, call_type: CallType | str) -> List[CallRecord]:
        """Return all CallRecord objects matching a call type classification."""
        type_str = call_type.value if isinstance(call_type, CallType) else str(call_type)
        ids = self._by_type.get(type_str, [])
        return [self.calls[c] for c in ids if c in self.calls]

    def __len__(self) -> int:
        return len(self.calls)
