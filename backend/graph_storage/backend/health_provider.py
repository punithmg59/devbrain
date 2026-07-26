"""
StorageHealthProvider interface and DefaultStorageHealthProvider implementation.
"""

import uuid
from abc import ABC, abstractmethod

from graph_storage.backend.storage_backend import StorageBackend
from graph_storage.exceptions import GraphStorageError
from graph_storage.model import ProbePolicy, SegmentId, StorageHealth


class StorageHealthProvider(ABC):
    """Abstract interface for inspecting backend health with configurable probe policies."""

    @abstractmethod
    def evaluate_health(
        self, backend: StorageBackend, policy: ProbePolicy = ProbePolicy.READ_WRITE
    ) -> StorageHealth:
        """Evaluate backend health using the specified probe policy."""
        ...


class DefaultStorageHealthProvider(StorageHealthProvider):
    """Default implementation of StorageHealthProvider supporting read/write probe policies."""

    def evaluate_health(
        self, backend: StorageBackend, policy: ProbePolicy = ProbePolicy.READ_WRITE
    ) -> StorageHealth:
        base_health = backend.health()
        if not base_health.is_healthy:
            return base_health

        if policy == ProbePolicy.READ_ONLY:
            return base_health

        probe_id = SegmentId(f"_health_probe_{uuid.uuid4().hex}")
        probe_payload = b"health_probe_data"
        try:
            backend.write_segment(probe_id, probe_payload)
            read_data = backend.read_segment(probe_id)
            if read_data != probe_payload:
                return StorageHealth(
                    is_healthy=False,
                    status_message="Health probe data mismatch during read check",
                    available_bytes=base_health.available_bytes,
                    used_bytes=base_health.used_bytes,
                )
            backend.delete_segment(probe_id)
            return base_health
        except GraphStorageError as e:
            return StorageHealth(
                is_healthy=False,
                status_message=f"Storage health probe failed: {e}",
                available_bytes=base_health.available_bytes,
                used_bytes=base_health.used_bytes,
            )
