"""
BackendRegistry for storage backend registration.
"""

from typing import Dict, Type
from graph_storage.backend.storage_backend import StorageBackend
from graph_storage.backend.backend_type import BackendType
from graph_storage.exceptions import GraphStorageError


class BackendRegistry:
    """Registry for storage backend class implementations."""

    _registry: Dict[BackendType, Type[StorageBackend]] = {}

    @classmethod
    def register(cls, backend_type: BackendType, backend_cls: Type[StorageBackend]) -> None:
        """Register a storage backend implementation class."""
        cls._registry[backend_type] = backend_cls

    @classmethod
    def get(cls, backend_type: BackendType) -> Type[StorageBackend]:
        """Retrieve the registered storage backend class for a backend type."""
        if backend_type not in cls._registry:
            raise GraphStorageError(f"No backend registered for type: {backend_type}")
        return cls._registry[backend_type]

    @classmethod
    def unregister(cls, backend_type: BackendType) -> None:
        """Unregister a backend type."""
        cls._registry.pop(backend_type, None)
