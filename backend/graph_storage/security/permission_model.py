"""
PermissionModel model definition.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class PermissionModel:
    """Immutable representation of a storage resource permission."""

    permission_id: str
    resource: str  # e.g., "segment", "snapshot", "partition", "*"
    operation: str  # e.g., "read", "write", "delete", "*"
    scope: str = "global"
    conditions: Dict[str, str] = field(default_factory=dict)
