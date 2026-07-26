"""
StorageLayout abstract interface and default implementation for filesystem layout.
"""

import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from graph_storage.config import StorageBackendConfig
from graph_storage.model import SegmentId, SnapshotId


class StorageLayout(ABC):
    """Abstract interface for filesystem directory layout organization."""

    @abstractmethod
    def segment_path(self, segment_id: SegmentId) -> Path:
        """Return the target file path for a segment."""
        ...

    @abstractmethod
    def temporary_segment_path(self, segment_id: SegmentId) -> Path:
        """Return a unique temporary file path for atomic segment writes."""
        ...

    @abstractmethod
    def snapshot_path(self, snapshot_id: SnapshotId) -> Path:
        """Return the file path for a snapshot descriptor."""
        ...

    @abstractmethod
    def manifest_path(self, manifest_id: str) -> Path:
        """Return the file path for a manifest catalog."""
        ...


class DefaultStorageLayout(StorageLayout):
    """Default local filesystem storage layout implementation."""

    def __init__(self, config: StorageBackendConfig):
        self.config = config
        self.root = config.root_directory.resolve()
        self.segments_dir = self.root / "segments"
        self.snapshots_dir = self.root / "snapshots"
        self.manifests_dir = self.root / "manifests"
        self.tmp_dir = (
            config.temporary_directory.resolve()
            if config.temporary_directory
            else self.root / "tmp"
        )

        self.segments_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def segment_path(self, segment_id: SegmentId) -> Path:
        safe_name = Path(segment_id.value).name
        return self.segments_dir / f"{safe_name}.segment"

    def temporary_segment_path(self, segment_id: SegmentId) -> Path:
        safe_name = Path(segment_id.value).name
        return self.tmp_dir / f".tmp_{safe_name}_{uuid.uuid4().hex}"

    def snapshot_path(self, snapshot_id: SnapshotId) -> Path:
        safe_name = Path(snapshot_id.value).name
        return self.snapshots_dir / f"{safe_name}.snapshot"

    def manifest_path(self, manifest_id: str) -> Path:
        safe_name = Path(manifest_id).name
        return self.manifests_dir / f"{safe_name}.manifest"
