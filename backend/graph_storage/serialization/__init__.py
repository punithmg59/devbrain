"""
Serialization package for Graph Storage byte encoding, decoding, and binary formats.
"""

from graph_storage.serialization.artifact_codec import ArtifactCodec
from graph_storage.serialization.artifact_codec_impl import BinaryCodec
from graph_storage.serialization.artifact_header import ArtifactHeader
from graph_storage.serialization.artifact_header_builder import ArtifactHeaderBuilder
from graph_storage.serialization.binary_decoder import BinaryDecoder
from graph_storage.serialization.binary_encoder import BinaryEncoder
from graph_storage.serialization.binary_format import (
    HEADER_FORMAT,
    HEADER_SIZE,
    MAGIC_BYTES,
    BinaryFormat,
    BinaryFormatSpec,
)
from graph_storage.serialization.checksum_provider import (
    BLAKE3Provider,
    CRC32Provider,
    ChecksumProvider,
    SHA256Provider,
    SHA512Provider,
)
from graph_storage.serialization.codec_registry import CodecRegistry, CodecType
from graph_storage.serialization.compression_strategy import (
    CompressionStrategy,
    NoCompression,
)
from graph_storage.serialization.serialization_pipeline import SerializationPipeline
from graph_storage.serialization.serialized_segment import SerializedSegment
from graph_storage.serialization.storage_artifact import StorageArtifact

__all__ = [
    "ArtifactCodec",
    "BinaryCodec",
    "ArtifactHeader",
    "ArtifactHeaderBuilder",
    "BinaryFormat",
    "BinaryFormatSpec",
    "HEADER_SIZE",
    "MAGIC_BYTES",
    "HEADER_FORMAT",
    "StorageArtifact",
    "SerializedSegment",
    "BinaryEncoder",
    "BinaryDecoder",
    "SerializationPipeline",
    "ChecksumProvider",
    "SHA256Provider",
    "CRC32Provider",
    "SHA512Provider",
    "BLAKE3Provider",
    "CompressionStrategy",
    "NoCompression",
    "CodecRegistry",
    "CodecType",
]
