"""
Unit tests for Serialization Layer (Step 4.5 Refinements).
"""

import io
import unittest
from graph_storage.exceptions import GraphStorageError, UnsupportedVersionError
from graph_storage.model import SegmentId, VersionRef
from graph_storage.serialization import (
    ArtifactHeader,
    ArtifactHeaderBuilder,
    BinaryCodec,
    BinaryDecoder,
    BinaryEncoder,
    BinaryFormat,
    CRC32Provider,
    CodecRegistry,
    CodecType,
    HEADER_SIZE,
    MAGIC_BYTES,
    NoCompression,
    SHA256Provider,
    SerializationPipeline,
    SerializedSegment,
    StorageArtifact,
)


class TestArtifactHeaderAndBuilder(unittest.TestCase):
    """Test suite for ArtifactHeader and ArtifactHeaderBuilder."""

    def test_header_builder(self):
        header = (
            ArtifactHeaderBuilder()
            .set_schema_version(VersionRef(1, 2, 3))
            .set_payload_length(2048)
            .build()
        )
        self.assertEqual(header.schema_version, VersionRef(1, 2, 3))
        self.assertEqual(header.payload_length, 2048)

        encoded = header.encode()
        self.assertEqual(len(encoded), HEADER_SIZE)

        decoded = ArtifactHeader.decode(encoded)
        self.assertEqual(decoded.magic_bytes, MAGIC_BYTES)
        self.assertEqual(decoded.schema_version, VersionRef(1, 2, 3))


class TestChecksumAndCompressionProviders(unittest.TestCase):
    """Test suite for ChecksumProvider and CompressionStrategy abstractions."""

    def test_sha256_provider(self):
        provider = SHA256Provider()
        checksum = provider.compute(b"test data")
        self.assertTrue(provider.verify(b"test data", checksum))

    def test_crc32_provider(self):
        provider = CRC32Provider()
        checksum = provider.compute(b"test data")
        self.assertTrue(provider.verify(b"test data", checksum))

    def test_no_compression(self):
        comp = NoCompression()
        self.assertEqual(comp.compression_name(), "none")
        self.assertEqual(comp.compress(b"data"), b"data")
        self.assertEqual(comp.decompress(b"data"), b"data")


class TestSerializationPipelineAndStreamIO(unittest.TestCase):
    """Test suite for SerializationPipeline and stream I/O."""

    def test_pipeline_stream_serialization(self):
        pipeline = SerializationPipeline()
        seg = SerializedSegment(
            segment_id=SegmentId("seg_pipe_1"),
            payload=b"stream pipeline payload",
            size_bytes=23,
            checksum="dummy",
            version=VersionRef(1, 0, 0),
        )

        encoded_bytes = pipeline.serialize_segment(seg)
        decoded_seg = pipeline.deserialize_segment(encoded_bytes)

        self.assertEqual(decoded_seg.segment_id, seg.segment_id)
        self.assertEqual(decoded_seg.payload, seg.payload)

    def test_binary_encoder_decoder_stream_io(self):
        encoder = BinaryEncoder()
        decoder = BinaryDecoder()

        seg = SerializedSegment(
            segment_id=SegmentId("seg_stream_1"),
            payload=b"stream io payload",
            size_bytes=17,
            checksum="dummy",
            version=VersionRef(1, 0, 0),
        )

        stream = io.BytesIO()
        bytes_written = encoder.encode_segment_stream(seg, stream)
        self.assertGreater(bytes_written, 0)

        stream.seek(0)
        decoded_seg = decoder.decode_segment_stream(stream)
        self.assertEqual(decoded_seg.segment_id, seg.segment_id)
        self.assertEqual(decoded_seg.payload, seg.payload)


class TestBinaryCodecAndRegistry(unittest.TestCase):
    """Test suite for BinaryCodec and CodecRegistry."""

    def test_codec_registry(self):
        codec_cls = CodecRegistry.get(CodecType.BINARY)
        self.assertEqual(codec_cls, BinaryCodec)

        codec_inst = CodecRegistry.create(CodecType.BINARY)
        self.assertIsInstance(codec_inst, BinaryCodec)

    def test_binary_codec_encode_decode(self):
        codec = BinaryCodec(supported_version=VersionRef(1, 0, 0))
        payload = b"raw codec byte payload"

        encoded = codec.encode(payload)
        self.assertTrue(codec.verify_artifact(encoded))

        decoded_artifact = codec.decode(encoded)
        self.assertEqual(decoded_artifact.payload, payload)

    def test_unsupported_version_decoding_raises_error(self):
        codec = BinaryCodec(supported_version=VersionRef(1, 0, 0))
        future_header = (
            ArtifactHeaderBuilder()
            .set_schema_version(VersionRef(2, 0, 0))
            .set_payload_length(10)
            .build()
        )
        future_bytes = future_header.encode() + b"0123456789"

        with self.assertRaises(UnsupportedVersionError):
            codec.decode(future_bytes)


if __name__ == "__main__":
    unittest.main()
