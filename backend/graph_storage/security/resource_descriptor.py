"""
ResourceDescriptor model definition.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class ResourceDescriptor:
    """Immutable target resource metadata descriptor."""

    resource_id: str
    resource_type: str  # "segment", "snapshot", "manifest", "partition", "cache", "transaction"
    owner: str = "system"
    classification: str = "STANDARD"  # "PUBLIC", "STANDARD", "CONFIDENTIAL", "RESTRICTED"
    metadata: Dict[str, str] = field(default_factory=dict)
