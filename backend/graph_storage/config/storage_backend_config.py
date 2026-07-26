"""
StorageBackendConfig implementation.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class StorageBackendConfig:
    """Immutable configuration for physical storage backends."""

    root_directory: Path
    read_only: bool = False
    atomic_write_enabled: bool = True
    maximum_segment_size: int = 104857600  # 100 MB default
    temporary_directory: Optional[Path] = None
