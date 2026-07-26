"""
Unit tests for Graph Storage backend implementations, registry, layout, factory, and health provider.
"""

import concurrent.futures
import tempfile
import unittest
from pathlib import Path

from graph_storage.backend import (
    BackendFactory,
    BackendRegistry,
    BackendType,
    DefaultStorageHealthProvider,
    DefaultStorageLayout,
    LocalFileBackend,
    MemoryBackend,
)
from graph_storage.config import StorageBackendConfig
from graph_storage.exceptions import (
    GraphStorageError,
    SegmentNotFoundError,
)
from graph_storage.model import ProbePolicy, SegmentId


class TestMemoryBackend(unittest.TestCase):
    """Test suite for MemoryBackend."""

    def setUp(self):
        self.backend = MemoryBackend()

    def test_crud_operations(self):
        seg_id = SegmentId("seg_mem_1")
        payload = b"hello memory storage"

        self.assertFalse(self.backend.exists_segment(seg_id))
        descriptor = self.backend.write_segment(seg_id, payload)
        self.assertEqual(descriptor.metadata.segment_id, seg_id)
        self.assertEqual(descriptor.metadata.size_bytes, len(payload))
        self.assertTrue(self.backend.exists_segment(seg_id))
        read_data = self.backend.read_segment(seg_id)
        self.assertEqual(read_data, payload)

        segments = self.backend.list_segments()
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].metadata.segment_id, seg_id)

        self.assertTrue(self.backend.delete_segment(seg_id))
        self.assertFalse(self.backend.exists_segment(seg_id))

    def test_read_non_existent_raises_exception(self):
        seg_id = SegmentId("non_existent")
        with self.assertRaises(SegmentNotFoundError):
            self.backend.read_segment(seg_id)

    def test_concurrent_reads_and_writes(self):
        backend = MemoryBackend()

        def writer(worker_id: int):
            for i in range(50):
                seg_id = SegmentId(f"worker_{worker_id}_seg_{i}")
                backend.write_segment(seg_id, f"data_{worker_id}_{i}".encode("utf-8"))

        def reader(worker_id: int):
            for i in range(50):
                seg_id = SegmentId(f"worker_{worker_id}_seg_{i}")
                if backend.exists_segment(seg_id):
                    backend.read_segment(seg_id)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            write_futures = [executor.submit(writer, w) for w in range(4)]
            read_futures = [executor.submit(reader, w) for w in range(4)]
            concurrent.futures.wait(write_futures + read_futures)

        listed = backend.list_segments()
        self.assertEqual(len(listed), 200)


class TestLocalFileBackend(unittest.TestCase):
    """Test suite for LocalFileBackend."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = StorageBackendConfig(root_directory=Path(self.temp_dir.name))
        self.backend = LocalFileBackend(config_or_path=self.config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_crud_operations(self):
        seg_id = SegmentId("seg_file_1")
        payload = b"hello local file storage"

        self.assertFalse(self.backend.exists_segment(seg_id))
        descriptor = self.backend.write_segment(seg_id, payload)
        self.assertEqual(descriptor.metadata.segment_id, seg_id)
        self.assertEqual(descriptor.metadata.size_bytes, len(payload))
        self.assertTrue(Path(descriptor.storage_key.value).is_file())

        self.assertTrue(self.backend.exists_segment(seg_id))
        read_data = self.backend.read_segment(seg_id)
        self.assertEqual(read_data, payload)

        segments = self.backend.list_segments()
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].metadata.segment_id, seg_id)

        self.assertTrue(self.backend.delete_segment(seg_id))
        self.assertFalse(self.backend.exists_segment(seg_id))

    def test_read_non_existent_raises_exception(self):
        seg_id = SegmentId("non_existent_file")
        with self.assertRaises(SegmentNotFoundError):
            self.backend.read_segment(seg_id)

    def test_storage_layout(self):
        layout = DefaultStorageLayout(self.config)
        seg_id = SegmentId("layout_test")
        seg_path = layout.segment_path(seg_id)
        self.assertEqual(seg_path.name, "layout_test.segment")
        self.assertEqual(seg_path.parent.name, "segments")


class TestBackendRegistryAndFactory(unittest.TestCase):
    """Test suite for BackendRegistry and BackendFactory."""

    def test_registry_get_and_create(self):
        self.assertEqual(BackendRegistry.get(BackendType.MEMORY), MemoryBackend)
        backend = BackendFactory.create(BackendType.MEMORY)
        self.assertIsInstance(backend, MemoryBackend)

    def test_unregistered_backend_raises_exception(self):
        with self.assertRaises(GraphStorageError):
            BackendFactory.create(BackendType.S3)


class TestStorageHealthProvider(unittest.TestCase):
    """Test suite for StorageHealthProvider."""

    def test_health_provider_read_write(self):
        backend = MemoryBackend()
        provider = DefaultStorageHealthProvider()
        health = provider.evaluate_health(backend, policy=ProbePolicy.READ_WRITE)
        self.assertTrue(health.is_healthy)

    def test_health_provider_read_only(self):
        backend = MemoryBackend()
        provider = DefaultStorageHealthProvider()
        health = provider.evaluate_health(backend, policy=ProbePolicy.READ_ONLY)
        self.assertTrue(health.is_healthy)


if __name__ == "__main__":
    unittest.main()
