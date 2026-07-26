"""
Pure Helper Utilities for Graph Query Engine.
"""

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TypeVar

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


class ImmutableHelper:
    """
    Helpers for immutability enforcement.
    """

    @staticmethod
    def freeze_dict(d: Mapping[K, V]) -> dict[K, V]:
        """
        Returns a shallow copy of dictionary.
        """
        return dict(d)

    @staticmethod
    def freeze_sequence(seq: Iterable[T]) -> tuple[T, ...]:
        """
        Converts an iterable into an immutable tuple.
        """
        return tuple(seq)


class CollectionHelper:
    """
    Utility methods for collection operations.
    """

    @staticmethod
    def chunk(sequence: Sequence[T], chunk_size: int) -> list[Sequence[T]]:
        """
        Splits a sequence into chunks of maximum size chunk_size.
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        return [sequence[i : i + chunk_size] for i in range(0, len(sequence), chunk_size)]


class ValidationHelper:
    """
    Helper methods for string and identifier checks.
    """

    @staticmethod
    def is_valid_identifier(ident: str) -> bool:
        """
        Validates if string is a non-empty alphanumeric identifier.
        """
        return bool(ident and isinstance(ident, str) and len(ident.strip()) > 0)


class PathHelper:
    """
    Helper methods for file and directory path validation.
    """

    @staticmethod
    def normalize(path_str: str | Path) -> Path:
        """
        Normalizes path representation.
        """
        return Path(path_str).resolve()

    @staticmethod
    def is_subpath(parent: str | Path, child: str | Path) -> bool:
        """
        Determines whether child path is located within parent directory.
        """
        p_norm = Path(parent).resolve()
        c_norm = Path(child).resolve()
        try:
            c_norm.relative_to(p_norm)
            return True
        except ValueError:
            return False
