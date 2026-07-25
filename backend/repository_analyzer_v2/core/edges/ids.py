"""
core/edges/ids.py
-----------------
EdgeID Value Object and Deterministic EdgeID Strategy.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional, Union
from pydantic import BaseModel, Field, field_validator

from core.edges.enums import EdgeKind
from core.edges.exceptions import EdgeIDError
from core.symbols import SymbolID

EDGE_ID_PATTERN = re.compile(r"^edge_[a-f0-9]{24}$")


class EdgeID(BaseModel):
    """
    Canonical Edge Identifier.
    Format: 'edge_' + 24 hexadecimal characters.
    """
    value: str = Field(..., description="Deterministic 29-character edge identifier")

    model_config = {
        "frozen": True
    }

    @field_validator("value", mode="before")
    @classmethod
    def _validate_value(cls, v: Any) -> str:
        if isinstance(v, dict) and "value" in v:
            v = v["value"]
        if isinstance(v, EdgeID):
            return v.value
        val_str = str(v).strip().lower()
        if not EDGE_ID_PATTERN.match(val_str):
            raise EdgeIDError(
                f"Invalid EdgeID format '{val_str}'. Must match pattern 'edge_[a-f0-9]{{24}}'."
            )
        return val_str

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"EdgeID({self.value!r})"


def generate_edge_id(
    repository_id: str,
    source_symbol_id: Union[SymbolID, str],
    target_symbol_id: Union[SymbolID, str],
    kind: Union[EdgeKind, str],
    discriminator: Optional[str] = None
) -> EdgeID:
    """
    Generate a deterministic, collision-resistant EdgeID for Step 4.

    Strategy:
    - Inputs: repository_id, source_symbol_id, target_symbol_id, relationship kind, optional discriminator.
    - Format: 'edge_' + first 24 hex characters of SHA-256 digest.

    Properties:
    - Stable across scans, parse versions, and machines.
    - Independent of traversal order and execution order.
    """
    if not repository_id or not repository_id.strip():
        raise EdgeIDError("repository_id cannot be empty when generating EdgeID.")

    source_str = source_symbol_id.value if isinstance(source_symbol_id, SymbolID) else str(source_symbol_id).strip()
    target_str = target_symbol_id.value if isinstance(target_symbol_id, SymbolID) else str(target_symbol_id).strip()
    kind_str = kind.value if isinstance(kind, EdgeKind) else str(kind).lower()
    disc_str = discriminator.strip() if discriminator else ""

    if not source_str or not target_str:
        raise EdgeIDError("source_symbol_id and target_symbol_id cannot be empty.")

    seed = f"{repository_id.strip()}::{source_str}::{target_str}::{kind_str}::{disc_str}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return EdgeID(value=f"edge_{digest}")
