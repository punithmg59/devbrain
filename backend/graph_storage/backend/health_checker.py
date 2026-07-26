"""
StorageHealthChecker implementation for backend health inspection.
"""

import uuid
from graph_storage.backend.storage_backend import StorageBackend
from graph_storage.exceptions import GraphStorageError
from graph_storage.model import SegmentId, StorageHealth


class StorageHealthChecker:
    """Utility component for evaluating storage backend health and I/O readiness."""

    def __init__(self, backend: StorageBackend):
        self.backend = backend

    def check(self) -> StorageHealth:
        base_health = self.backend.health()
        if not base_health.is_healthy:
            return base_health

        probe_id = SegmentId(f"_health_probe_{uuid.uuid4().hex}")
        probe_payload = b"health_probe_data"
        try:
            self.backend.write_segment(probe_id, probe_payload)
            read_data = self.backend.read_segment(probe_id)
            if read_data != probe_payload:
                return StorageHealth(
                    is_healthy=False,
                    status_message="Health probe data mismatch during read check",
                    available_bytes=base_health.available_bytes,
                    used_bytes=base_health.used_bytes,
                )
            self.backend.delete_segment(probe_id)
            return base_health
        except GraphStorageError as e:
            return StorageHealth(
                is_healthy=False,
                status_message=f"Storage health probe failed: {e}",
                available_bytes=base_health.available_bytes,
                used_bytes=base_health.used_bytes,
            )
