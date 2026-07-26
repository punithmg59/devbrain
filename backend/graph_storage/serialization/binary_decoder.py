"""
BinaryDecoder implementation supporting stream and byte array deserialization.
"""

import io
from typing import BinaryIO, Optional

from graph_storage.exceptions import ArtifactCorruptedError, HeaderDecodeError
from graph_storage.model import SegmentId
from graph_storage.serialization.artifact_header import ArtifactHeader
from graph_storage.serialization.binary_format import HEADER_SIZE
from graph_storage.serialization.checksum_provider import ChecksumProvider, SHA256Provider
from graph_storage.serialization.compression_strategy import CompressionStrategy, NoCompression
from graph_storage.serialization.serialized_segment import SerializedSegment
from graph_storage.serialization.storage_artifact import StorageArtifact


class BinaryDecoder:
    """Decoder validating binary streams and reconstructing storage artifacts."""

    def __init__(
        self,
        checksum_provider: Optional[ChecksumProvider] = None,
        compression_strategy: Optional[CompressionStrategy] = None,
    ):
        self.checksum_provider = checksum_provider or SHA256Provider()
        self.compression_strategy = compression_strategy or NoCompression()

    @classmethod
    def decode_header(cls, data: bytes) -> ArtifactHeader:
        """Decode header from bytes."""
        try:
            return ArtifactHeader.decode(data)
        except Exception as e:
            raise HeaderDecodeError(f"Failed to decode artifact header: {e}") from e

    @classmethod
    def decode_header_stream(cls, stream: BinaryIO) -> ArtifactHeader:
        """Decode header from an input stream."""
        header_bytes = stream.read(HEADER_SIZE)
        if len(header_bytes) < HEADER_SIZE:
            raise HeaderDecodeError(
                f"Stream ended prematurely while reading header ({len(header_bytes)}/{HEADER_SIZE} bytes)"
            )
        return cls.decode_header(header_bytes)

    def decode_segment_stream(self, stream: BinaryIO) -> SerializedSegment:
        """Decode a SerializedSegment from an input stream."""
        header = self.decode_header_stream(stream)
        payload_section = stream.read(header.payload_length)

        if len(payload_section) < header.payload_length:
            raise ArtifactCorruptedError(
                f"Truncated artifact stream: expected {header.payload_length} bytes, got {len(payload_section)} bytes"
            )

        if len(payload_section) < 2:
            raise ArtifactCorruptedError("Malformed payload section: missing segment ID length header")

        id_len = int.from_bytes(payload_section[:2], "big")
        if len(payload_section) < 2 + id_len:
            raise ArtifactCorruptedError("Malformed payload section: truncated segment ID string")

        seg_id_str = payload_section[2 : 2 + id_len].decode("utf-8")
        compressed_payload = payload_section[2 + id_len :]
        payload = self.compression_strategy.decompress(compressed_payload)

        checksum = self.checksum_provider.compute(payload)

        return SerializedSegment(
            segment_id=SegmentId(seg_id_str),
            payload=payload,
            size_bytes=len(payload),
            checksum=checksum,
            version=header.schema_version,
            compression_type=self.compression_strategy.compression_name(),
        )

    def decode_segment(self, data: bytes) -> SerializedSegment:
        """Decode a SerializedSegment from a bytes buffer."""
        stream = io.BytesIO(data)
        return self.decode_segment_stream(stream)

    def decode_artifact(self, data: bytes) -> StorageArtifact:
        """Decode a StorageArtifact from a bytes buffer."""
        header = self.decode_header(data)
        payload = data[HEADER_SIZE : HEADER_SIZE + header.payload_length]
        checksum = self.checksum_provider.compute(payload)
        return StorageArtifact(
            header=header,
            payload=payload,
            checksum=checksum,
            version=header.schema_version,
            metadata_reference=f"artifact_v{header.schema_version.major}",
        )
