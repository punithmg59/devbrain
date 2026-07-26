"""
StorageArtifact model definition.
"""

from dataclasses import dataclass
from graph_storage.model import VersionRef
from graph_storage.serialization.artifact_header import ArtifactHeader


@dataclass(frozen=True)
class StorageArtifact:
    """Immutable representation of a complete serialized storage artifact."""

    header: ArtifactHeader
    payload: bytes
    checksum: str
    version: VersionRef
    metadata_reference: str
