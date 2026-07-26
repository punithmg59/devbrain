"""
LocalFileBackend implementation for Graph Storage.
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import List, Optional, Union

from graph_storage.backend.storage_backend import StorageBackend
from graph_storage.backend.storage_layout import DefaultStorageLayout, StorageLayout
from graph_storage.config import StorageBackendConfig
from graph_storage.exceptions import (
    BackendUnavailableError,
    SegmentNotFoundError,
    StorageIOError,
    StoragePermissionError,
)
from graph_storage.model import (
    PartitionId,
    SegmentDescriptor,
    SegmentId,
    SegmentMetadata,
    StorageHealth,
    StorageKey,
)


class LocalFileBackend(StorageBackend):
    """Local filesystem storage backend using StorageLayout and atomic writes."""

    def __init__(
        self,
        config_or_path: Union[StorageBackendConfig, str, Path],
        layout: Optional[StorageLayout] = None,
    ):
        if isinstance(config_or_path, StorageBackendConfig):
            self.config = config_or_path
        else:
            self.config = StorageBackendConfig(root_directory=Path(config_or_path))

        self.layout = layout or DefaultStorageLayout(self.config)

    def exists_segment(self, segment_id: SegmentId) -> bool:
        try:
            return self.layout.segment_path(segment_id).is_file()
        except PermissionError as e:
            raise StoragePermissionError(f"Permission denied checking existence for {segment_id.value}") from e
        except OSError as e:
            raise StorageIOError(f"Failed to check existence of segment {segment_id.value}: {e}") from e

    def read_segment(self, segment_id: SegmentId) -> bytes:
        path = self.layout.segment_path(segment_id)
        if not path.is_file():
            raise SegmentNotFoundError(f"Segment not found: {segment_id.value}")
        try:
            return path.read_bytes()
        except PermissionError as e:
            raise StoragePermissionError(f"Permission denied reading segment {segment_id.value}") from e
        except OSError as e:
            raise StorageIOError(f"Failed to read segment {segment_id.value}: {e}") from e

    def write_segment(self, segment_id: SegmentId, data: bytes) -> SegmentDescriptor:
        if self.config.read_only:
            raise StoragePermissionError(f"Cannot write segment {segment_id.value}: Backend is read-only")
        if len(data) > self.config.maximum_segment_size:
            raise StorageIOError(
                f"Segment size ({len(data)} bytes) exceeds maximum limit ({self.config.maximum_segment_size} bytes)"
            )

        target_path = self.layout.segment_path(segment_id)

        if self.config.atomic_write_enabled:
            tmp_path = self.layout.temporary_segment_path(segment_id)
            try:
                with open(tmp_path, "wb") as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
                tmp_path.replace(target_path)
                # Durability sync on parent directory
                try:
                    parent_dir = target_path.parent
                    dir_fd = os.open(parent_dir, os.O_RDONLY)
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
                except (OSError, AttributeError):
                    pass
            except PermissionError as e:
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
                raise StoragePermissionError(f"Permission denied writing segment {segment_id.value}") from e
            except OSError as e:
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
                raise StorageIOError(f"Failed atomic write for segment {segment_id.value}: {e}") from e
        else:
            try:
                with open(target_path, "wb") as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
            except PermissionError as e:
                raise StoragePermissionError(f"Permission denied writing segment {segment_id.value}") from e
            except OSError as e:
                raise StorageIOError(f"Failed writing segment {segment_id.value}: {e}") from e

        checksum = hashlib.sha256(data).hexdigest()
        metadata = SegmentMetadata(
            segment_id=segment_id,
            partition_id=PartitionId("local_default"),
            size_bytes=len(data),
            record_count=1,
            checksum=checksum,
        )
        return SegmentDescriptor(
            metadata=metadata,
            storage_key=StorageKey(str(target_path)),
        )

    def delete_segment(self, segment_id: SegmentId) -> bool:
        if self.config.read_only:
            raise StoragePermissionError(f"Cannot delete segment {segment_id.value}: Backend is read-only")
        path = self.layout.segment_path(segment_id)
        if not path.is_file():
            return False
        try:
            path.unlink()
            return True
        except PermissionError as e:
            raise StoragePermissionError(f"Permission denied deleting segment {segment_id.value}") from e
        except OSError as e:
            raise StorageIOError(f"Failed deleting segment {segment_id.value}: {e}") from e

    def list_segments(self) -> List[SegmentDescriptor]:
        descriptors: List[SegmentDescriptor] = []
        try:
            segments_dir = self.layout.segment_path(SegmentId("dummy")).parent
            for item in segments_dir.glob("*.segment"):
                if item.is_file():
                    seg_id_val = item.stem
                    data = item.read_bytes()
                    checksum = hashlib.sha256(data).hexdigest()
                    metadata = SegmentMetadata(
                        segment_id=SegmentId(seg_id_val),
                        partition_id=PartitionId("local_default"),
                        size_bytes=len(data),
                        record_count=1,
                        checksum=checksum,
                    )
                    descriptors.append(
                        SegmentDescriptor(
                            metadata=metadata,
                            storage_key=StorageKey(str(item)),
                        )
                    )
            return descriptors
        except PermissionError as e:
            raise StoragePermissionError("Permission denied listing segments") from e
        except OSError as e:
            raise StorageIOError(f"Failed listing storage segments: {e}") from e

    def health(self) -> StorageHealth:
        try:
            total, used, available = shutil.disk_usage(self.config.root_directory)
            return StorageHealth(
                is_healthy=True,
                status_message="Local filesystem backend operational",
                available_bytes=available,
                used_bytes=used,
            )
        except Exception as e:
            return StorageHealth(
                is_healthy=False,
                status_message=f"Local storage unhealthy: {e}",
                available_bytes=0,
                used_bytes=0,
            )
