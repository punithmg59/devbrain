"""
Principal model definition.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class Principal:
    """Immutable identity representation for an authenticated security principal."""

    principal_id: str
    username: str
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    authenticated_time: float = field(default_factory=time.time)
