"""
CodecRegistry for registering and looking up ArtifactCodec implementations.
"""

from enum import Enum, auto
from typing import Dict, Type
from graph_storage.exceptions import GraphStorageError
from graph_storage.serialization.artifact_codec import ArtifactCodec
from graph_storage.serialization.artifact_codec_impl import BinaryCodec


class CodecType(Enum):
    """Supported serialization codec types."""
    BINARY = auto()
    JSON = auto()
    PROTOBUF = auto()
    FLATBUFFERS = auto()


class CodecRegistry:
    """Registry for registering and retrieving ArtifactCodec classes."""

    _registry: Dict[CodecType, Type[ArtifactCodec]] = {
        CodecType.BINARY: BinaryCodec,
    }

    @classmethod
    def register(cls, codec_type: CodecType, codec_cls: Type[ArtifactCodec]) -> None:
        """Register an ArtifactCodec implementation."""
        cls._registry[codec_type] = codec_cls

    @classmethod
    def get(cls, codec_type: CodecType) -> Type[ArtifactCodec]:
        """Retrieve registered ArtifactCodec class for given type."""
        if codec_type not in cls._registry:
            raise GraphStorageError(f"No codec registered for type: {codec_type}")
        return cls._registry[codec_type]

    @classmethod
    def create(cls, codec_type: CodecType, **kwargs) -> ArtifactCodec:
        """Instantiate an ArtifactCodec instance."""
        codec_cls = cls.get(codec_type)
        return codec_cls(**kwargs)
