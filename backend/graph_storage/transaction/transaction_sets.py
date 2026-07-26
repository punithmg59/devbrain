"""
ReadSet and WriteSet model definitions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ReadEntry:
    key: str
    version: str
    read_time: float


@dataclass
class WriteEntry:
    key: str
    before_image: Optional[bytes]
    after_image: Optional[bytes]
    operation: str  # "PUT", "DELETE", "UPDATE"


class ReadSet:
    """Tracks read items during a transaction."""

    def __init__(self):
        self._reads: Dict[str, ReadEntry] = {}

    def add(self, key: str, version: str, read_time: float) -> None:
        self._reads[key] = ReadEntry(key=key, version=version, read_time=read_time)

    def get(self, key: str) -> Optional[ReadEntry]:
        return self._reads.get(key)

    def entries(self) -> List[ReadEntry]:
        return list(self._reads.values())

    def keys(self) -> List[str]:
        return list(self._reads.keys())


class WriteSet:
    """Tracks modified items during a transaction."""

    def __init__(self):
        self._writes: Dict[str, WriteEntry] = {}

    def add(self, key: str, before_image: Optional[bytes], after_image: Optional[bytes], operation: str = "PUT") -> None:
        self._writes[key] = WriteEntry(
            key=key, before_image=before_image, after_image=after_image, operation=operation
        )

    def get(self, key: str) -> Optional[WriteEntry]:
        return self._writes.get(key)

    def entries(self) -> List[WriteEntry]:
        return list(self._writes.values())

    def keys(self) -> List[str]:
        return list(self._writes.keys())
