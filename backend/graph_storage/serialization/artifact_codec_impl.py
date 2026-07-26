"""
BinaryCodec implementation of the ArtifactCodec interface using SerializationPipeline.
"""

from typing import Any, Optional
from graph_storage.exceptions import GraphStorageError, UnsupportedVersionError
from graph_storage.model import ArtifactHeader as ModelArtifactHeader, VersionRef
from graph_storage.serialization.artifact_codec import ArtifactCodec
from graph_storage.serialization.artifact_header import ArtifactHeader
from graph_storage.serialization.binary_format import HEADER_SIZE
from graph_storage.serialization.checksum_provider import ChecksumProvider
from graph_storage.serialization.compression_strategy import CompressionStrategy
from graph_storage.serialization.serialization_pipeline import SerializationPipeline
from graph_storage.serialization.serialized_segment import SerializedSegment
from graph_storage.serialization.storage_artifact import StorageArtifact


class BinaryCodec(ArtifactCodec):
    """Concrete binary codec implementing ArtifactCodec contract via SerializationPipeline."""

    def __init__(
        self,
        supported_version: VersionRef = VersionRef(1, 0, 0),
        checksum_provider: Optional[ChecksumProvider] = None,
        compression_strategy: Optional[CompressionStrategy] = None,
    ):
        self._supported_version = supported_version
        self.pipeline = SerializationPipeline(checksum_provider, compression_strategy)

    def encode(self, payload: Any) -> bytes:
        """Encode in-memory artifact payload into raw bytes."""
        if isinstance(payload, SerializedSegment):
            return self.pipeline.serialize_segment(payload, schema_version=self._supported_version)
        elif isinstance(payload, StorageArtifact):
            return self.pipeline.serialize_artifact(payload)
        elif isinstance(payload, bytes):
            checksum = self.pipeline.checksum_provider.compute(payload)
            header = (
                self.pipeline.create_header_builder()
                .set_schema_version(self._supported_version)
                .set_payload_length(len(payload))
                .build()
            )
            artifact = StorageArtifact(
                header=header,
                payload=payload,
                checksum=checksum,
                version=self._supported_version,
                metadata_reference="raw_payload",
            )
            return self.pipeline.serialize_artifact(artifact)
        else:
            raise GraphStorageError(f"Unsupported payload type for BinaryCodec: {type(payload)}")

    def decode(self, data: bytes) -> Any:
        """Decode raw bytes back into in-memory artifact payload."""
        header = self.pipeline.decoder.decode_header(data)
        if header.schema_version.major > self._supported_version.major:
            raise UnsupportedVersionError(
                f"Unsupported forward schema version: {header.schema_version.major}.{header.schema_version.minor}. "
                f"Codec supports up to major version {self._supported_version.major}"
            )
        return self.pipeline.deserialize_artifact(data)

    def header(self, data: bytes) -> ModelArtifactHeader:
        """Extract header descriptor from binary data."""
        header = self.pipeline.decoder.decode_header(data)
        payload_data = data[HEADER_SIZE : HEADER_SIZE + header.payload_length]
        checksum = self.pipeline.checksum_provider.compute(payload_data)
        return ModelArtifactHeader(
            magic_bytes=header.magic_bytes,
            schema_version=header.schema_version,
            payload_size_bytes=header.payload_length,
            checksum=checksum,
        )

    def schema_version(self) -> VersionRef:
        """Return supported schema version."""
        return self._supported_version

    def verify_artifact(self, data: bytes) -> bool:
        """Verify binary artifact format, magic bytes, and checksum."""
        try:
            header = self.pipeline.decoder.decode_header(data)
            payload = data[HEADER_SIZE : HEADER_SIZE + header.payload_length]
            return len(payload) == header.payload_length
        except Exception:
            return False
