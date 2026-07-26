"""
SerializationPipeline orchestrating header building, encoding, integrity, compression, and decoding.
"""

from typing import BinaryIO, Optional
from graph_storage.model import VersionRef
from graph_storage.serialization.artifact_header_builder import ArtifactHeaderBuilder
from graph_storage.serialization.binary_decoder import BinaryDecoder
from graph_storage.serialization.binary_encoder import BinaryEncoder
from graph_storage.serialization.checksum_provider import ChecksumProvider, SHA256Provider
from graph_storage.serialization.compression_strategy import CompressionStrategy, NoCompression
from graph_storage.serialization.serialized_segment import SerializedSegment
from graph_storage.serialization.storage_artifact import StorageArtifact


class SerializationPipeline:
    """Modular pipeline handling end-to-end serialization operations."""

    def __init__(
        self,
        checksum_provider: Optional[ChecksumProvider] = None,
        compression_strategy: Optional[CompressionStrategy] = None,
    ):
        self.checksum_provider = checksum_provider or SHA256Provider()
        self.compression_strategy = compression_strategy or NoCompression()
        self.encoder = BinaryEncoder(self.checksum_provider, self.compression_strategy)
        self.decoder = BinaryDecoder(self.checksum_provider, self.compression_strategy)

    def create_header_builder(self) -> ArtifactHeaderBuilder:
        """Create a new ArtifactHeaderBuilder configured with pipeline settings."""
        return (
            ArtifactHeaderBuilder()
            .set_checksum_algorithm_id(self.checksum_provider.algorithm_id())
        )

    def serialize_segment(
        self,
        segment: SerializedSegment,
        schema_version: VersionRef = VersionRef(1, 0, 0),
    ) -> bytes:
        """Serialize a segment payload through the pipeline."""
        return self.encoder.encode_segment(segment, schema_version=schema_version)

    def deserialize_segment(self, data: bytes) -> SerializedSegment:
        """Deserialize a segment payload through the pipeline."""
        return self.decoder.decode_segment(data)

    def serialize_artifact(self, artifact: StorageArtifact) -> bytes:
        """Serialize a storage artifact through the pipeline."""
        return self.encoder.encode_artifact(artifact)

    def deserialize_artifact(self, data: bytes) -> StorageArtifact:
        """Deserialize a storage artifact through the pipeline."""
        return self.decoder.decode_artifact(data)
