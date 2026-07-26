"""
Engine Version Contract.

Prepares for Graph Storage schema evolution and engine compatibility.
"""

from typing import Protocol


class IEngineVersion(Protocol):
    """
    Contract representing the Graph Query Engine software version.
    """

    @property
    def major(self) -> int:
        """Major version number."""
        ...

    @property
    def minor(self) -> int:
        """Minor version number."""
        ...

    @property
    def patch(self) -> int:
        """Patch version number."""
        ...

    def to_version_string(self) -> str:
        """Returns semantic version string."""
        ...


__all__ = ["IEngineVersion"]
