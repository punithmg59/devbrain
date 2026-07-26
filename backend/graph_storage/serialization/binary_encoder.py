"""
BinaryEncoder implementation supporting stream and byte array serialization.
"""

import io
from typing import BinaryIO, Optional

from graph_storage.model import VersionRef
from graph_storage.serialization.artifact_header_builder import ArtifactHeaderBuilder
from graph_storage.serialization.checksum_provider import ChecksumProvider, SHA256Provider
from graph_storage.serialization.compression_strategy import CompressionStrategy, NoCompression
from graph_storage.serialization.serialized_segment import SerializedSegment
from graph_storage.serialization.storage_artifact import StorageArtifact


class BinaryEncoder:
    """Encoder converting storage objects and segments into binary streams or bytes."""

    def __init__(
        self,
        checksum_provider: Optional[ChecksumProvider] = None,
        compression_strategy: Optional[CompressionStrategy] = None,
    ):
        self.checksum_provider = checksum_provider or SHA256Provider()
        self.compression_strategy = compression_strategy or NoCompression()

    def encode_segment_stream(
        self,
        segment: SerializedSegment,
        output_stream: BinaryIO,
        schema_version: VersionRef = VersionRef(1, 0, 0),
        encoding_version: VersionRef = VersionRef(1, 0, 0),
    ) -> int:
        """Encode segment into an output stream and return total bytes written."""
        payload_bytes = self.compression_strategy.compress(segment.payload)

        seg_id_bytes = segment.segment_id.value.encode("utf-8")
        id_header = len(seg_id_bytes).to_bytes(2, "big") + seg_id_bytes
        full_payload = id_header + payload_bytes

        header = (
            ArtifactHeaderBuilder()
            .set_schema_version(schema_version)
            .set_encoding_version(encoding_version)
            .set_checksum_algorithm_id(self.checksum_provider.algorithm_id())
            .set_payload_length(len(full_payload))
            .build()
        )

        header_bytes = header.encode()
        output_stream.write(header_bytes)
        output_stream.write(full_payload)
        return len(header_bytes) + len(full_payload)

    def encode_segment(
        self,
        segment: SerializedSegment,
        schema_version: VersionRef = VersionRef(1, 0, 0),
        encoding_version: VersionRef = VersionRef(1, 0, 0),
    ) -> bytes:
        """Encode segment into a bytes buffer."""
        stream = io.BytesIO()
        self.encode_segment_stream(segment, stream, schema_version, encoding_version)
        return stream.getvalue()

    def encode_artifact(self, artifact: StorageArtifact) -> bytes:
        """Encode StorageArtifact into bytes buffer."""
        return artifact.header.encode() + artifact.payload
