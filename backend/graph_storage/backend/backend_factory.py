"""
BackendFactory delegating to BackendRegistry.
"""

from typing import Any

from graph_storage.backend.backend_registry import BackendRegistry
from graph_storage.backend.backend_type import BackendType
from graph_storage.backend.storage_backend import StorageBackend


class BackendFactory:
    """Factory for instantiating storage backends via BackendRegistry."""

    @classmethod
    def create(cls, backend_type: BackendType, **kwargs: Any) -> StorageBackend:
        """Instantiate a storage backend using the registered backend class."""
        backend_cls = BackendRegistry.get(backend_type)
        return backend_cls(**kwargs)
