"""
core/symbol_identity/ids.py
----------------------------
Deterministic SymbolID strategy functions for Step 3.4.
"""

from __future__ import annotations

import hashlib
from typing import Optional, Union

from core.symbols import Language, QualifiedName, SymbolID, SymbolKind
from core.symbols.exceptions import SymbolIDError


def generate_canonical_symbol_id(
    repository_id: str,
    language: Union[Language, str],
    fqn: Union[QualifiedName, str],
    kind: Union[SymbolKind, str],
    overload_discriminator: Optional[str] = None
) -> SymbolID:
    """
    Generate a deterministic, collision-resistant canonical SymbolID for Step 3.4.

    Strategy:
    - Inputs: repository_id, language, canonical qualified name, symbol kind, optional overload discriminator.
    - Format: 'sym_' + first 24 hex characters of SHA-256 digest.

    Properties:
    - Stable across scans, parse versions, and machines.
    - Independent of memory location and execution order.
    """
    if not repository_id or not repository_id.strip():
        raise SymbolIDError("repository_id cannot be empty when generating canonical SymbolID.")

    lang_str = language.value if isinstance(language, Language) else str(language).lower()
    fqn_str = fqn.to_string() if isinstance(fqn, QualifiedName) else str(fqn).strip()
    kind_str = kind.value if isinstance(kind, SymbolKind) else str(kind).lower()
    overload_str = overload_discriminator.strip() if overload_discriminator else ""

    if not fqn_str:
        raise SymbolIDError("Fully qualified name cannot be empty when generating canonical SymbolID.")

    seed = f"{repository_id.strip()}::{lang_str}::{fqn_str}::{kind_str}::{overload_str}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return SymbolID(value=f"sym_{digest}")
