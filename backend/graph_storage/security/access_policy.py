"""
AccessPolicy model definition.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class AccessPolicy:
    """Immutable access policy rule configuration."""

    allow_rules: List[str] = field(default_factory=lambda: ["*"])
    deny_rules: List[str] = field(default_factory=list)
    priority: int = 100
    conditions: Dict[str, str] = field(default_factory=dict)
    inheritance: bool = True
