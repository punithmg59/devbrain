"""
ArtifactHeaderBuilder for constructing and validating ArtifactHeader instances.
"""

from typing import Optional
from graph_storage.exceptions import SerializationError
from graph_storage.model import VersionRef
from graph_storage.serialization.artifact_header import ArtifactHeader
from graph_storage.serialization.binary_format import HEADER_SIZE, MAGIC_BYTES


class ArtifactHeaderBuilder:
    """Builder pattern for constructing valid ArtifactHeader instances."""

    def __init__(self):
        self._magic_bytes: bytes = MAGIC_BYTES
        self._schema_version: VersionRef = VersionRef(1, 0, 0)
        self._encoding_version: VersionRef = VersionRef(1, 0, 0)
        self._checksum_algorithm_id: int = 1  # SHA256 default
        self._payload_length: int = 0
        self._flags: int = 0
        self._reserved: bytes = b"\x00" * 8

    def set_schema_version(self, version: VersionRef) -> "ArtifactHeaderBuilder":
        self._schema_version = version
        return self

    def set_encoding_version(self, version: VersionRef) -> "ArtifactHeaderBuilder":
        self._encoding_version = version
        return self

    def set_checksum_algorithm_id(self, alg_id: int) -> "ArtifactHeaderBuilder":
        self._checksum_algorithm_id = alg_id
        return self

    def set_payload_length(self, length: int) -> "ArtifactHeaderBuilder":
        if length < 0:
            raise SerializationError("Payload length cannot be negative")
        self._payload_length = length
        return self

    def set_flags(self, flags: int) -> "ArtifactHeaderBuilder":
        self._flags = flags
        return self

    def build(self) -> ArtifactHeader:
        """Construct and return a validated ArtifactHeader."""
        return ArtifactHeader(
            magic_bytes=self._magic_bytes,
            schema_version=self._schema_version,
            encoding_version=self._encoding_version,
            checksum_algorithm_id=self._checksum_algorithm_id,
            payload_length=self._payload_length,
            flags=self._flags,
            reserved=self._reserved,
        )
