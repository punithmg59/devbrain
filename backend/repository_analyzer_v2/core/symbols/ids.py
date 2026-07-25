"""
core/symbols/ids.py
-------------------
Deterministic SymbolID and NamespaceID Value Objects and strategy functions.
"""

from __future__ import annotations

import hashlib
from typing import Optional, Union
from pydantic import BaseModel, Field, field_validator

from core.symbols.enums import Language, SymbolKind
from core.symbols.exceptions import SymbolIDError
from core.symbols.qualified_name import QualifiedName


class SymbolID(BaseModel):
    """
    Deterministic, immutable Symbol Identifier.
    
    Format: 'sym_<24-character-sha256-hex>'
    """
    value: str = Field(..., description="Deterministic symbol identifier string")

    model_config = {
        "frozen": True
    }

    @field_validator("value")
    @classmethod
    def _validate_value(cls, v: str) -> str:
        if not v or not v.startswith("sym_"):
            raise SymbolIDError(f"SymbolID value must be non-empty and start with 'sym_'. Got: '{v}'")
        return v

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SymbolID):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False


class NamespaceID(BaseModel):
    """
    Deterministic, immutable Namespace Identifier.
    
    Format: 'ns_<24-character-sha256-hex>'
    """
    value: str = Field(..., description="Deterministic namespace identifier string")

    model_config = {
        "frozen": True
    }

    @field_validator("value")
    @classmethod
    def _validate_value(cls, v: str) -> str:
        if not v or not v.startswith("ns_"):
            raise SymbolIDError(f"NamespaceID value must be non-empty and start with 'ns_'. Got: '{v}'")
        return v

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, NamespaceID):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False


def generate_symbol_id(
    repository_id: str,
    language: Union[Language, str],
    fqn: Union[QualifiedName, str],
    kind: Union[SymbolKind, str],
    disambiguator: Optional[str] = None
) -> SymbolID:
    """
    Generate a deterministic, collision-resistant SymbolID.

    Strategy:
    - Inputs: repository_id, language, qualified name, symbol kind, optional overload/signature disambiguator.
    - Algorithm: SHA-256 digest of concatenated canonical representation.
    - Format: 'sym_' + first 24 hex characters of SHA-256 hash.

    Properties:
    - Stable across parses, machines, and execution environments.
    - Memory-independent and parse-order-independent.
    """
    if not repository_id or not repository_id.strip():
        raise SymbolIDError("repository_id cannot be empty when generating SymbolID.")

    lang_str = language.value if isinstance(language, Language) else str(language).lower()
    fqn_str = fqn.to_string() if isinstance(fqn, QualifiedName) else str(fqn).strip()
    kind_str = kind.value if isinstance(kind, SymbolKind) else str(kind).lower()
    disambig_str = disambiguator.strip() if disambiguator else ""

    if not fqn_str:
        raise SymbolIDError("Fully qualified name cannot be empty when generating SymbolID.")

    seed = f"{repository_id.strip()}::{lang_str}::{fqn_str}::{kind_str}::{disambig_str}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return SymbolID(value=f"sym_{digest}")


def generate_namespace_id(
    repository_id: str,
    language: Union[Language, str],
    fqn: Union[QualifiedName, str]
) -> NamespaceID:
    """
    Generate a deterministic NamespaceID.
    """
    if not repository_id or not repository_id.strip():
        raise SymbolIDError("repository_id cannot be empty when generating NamespaceID.")

    lang_str = language.value if isinstance(language, Language) else str(language).lower()
    fqn_str = fqn.to_string() if isinstance(fqn, QualifiedName) else str(fqn).strip()

    seed = f"{repository_id.strip()}::{lang_str}::namespace::{fqn_str}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return NamespaceID(value=f"ns_{digest}")
