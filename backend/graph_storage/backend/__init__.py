"""
Backend package for Graph Storage drivers and storage engines.
"""

from graph_storage.backend.backend_type import BackendType
from graph_storage.backend.backend_registry import BackendRegistry
from graph_storage.backend.backend_factory import BackendFactory
from graph_storage.backend.consistency_coordinator import ConsistencyCoordinator
from graph_storage.backend.health_provider import (
    DefaultStorageHealthProvider,
    StorageHealthProvider,
)
from graph_storage.backend.local_file_backend import LocalFileBackend
from graph_storage.backend.memory_backend import MemoryBackend
from graph_storage.backend.storage_backend import StorageBackend
from graph_storage.backend.storage_layout import DefaultStorageLayout, StorageLayout

# Register standard backends in registry
BackendRegistry.register(BackendType.LOCAL, LocalFileBackend)
BackendRegistry.register(BackendType.MEMORY, MemoryBackend)

__all__ = [
    "StorageBackend",
    "ConsistencyCoordinator",
    "LocalFileBackend",
    "MemoryBackend",
    "BackendFactory",
    "BackendRegistry",
    "BackendType",
    "StorageLayout",
    "DefaultStorageLayout",
    "StorageHealthProvider",
    "DefaultStorageHealthProvider",
]
