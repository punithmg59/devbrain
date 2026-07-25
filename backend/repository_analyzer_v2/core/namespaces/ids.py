"""
core/namespaces/ids.py
----------------------
Deterministic NamespaceID strategy functions.
"""

from __future__ import annotations

import hashlib
from typing import Optional, Union

from core.namespaces.enums import NamespaceKind
from core.symbols.enums import Language
from core.symbols.exceptions import SymbolIDError
from core.symbols.ids import NamespaceID
from core.symbols.qualified_name import QualifiedName


def generate_scope_namespace_id(
    repository_id: str,
    language: Union[Language, str],
    file_path: Optional[str],
    fqn: Union[QualifiedName, str],
    kind: Union[NamespaceKind, str],
    scope_index: int = 0
) -> NamespaceID:
    """
    Generate a deterministic, collision-resistant NamespaceID for a scope boundary.

    Strategy:
    - Inputs: repository_id, language, file_path, fqn, kind, scope_index.
    - Format: 'ns_' + first 24 hex characters of SHA-256 digest.
    """
    if not repository_id or not repository_id.strip():
        raise SymbolIDError("repository_id cannot be empty when generating NamespaceID.")

    lang_str = language.value if isinstance(language, Language) else str(language).lower()
    fp_str = file_path.strip() if file_path else "repo_root"
    fqn_str = fqn.to_string() if isinstance(fqn, QualifiedName) else str(fqn).strip()
    kind_str = kind.value if isinstance(kind, NamespaceKind) else str(kind).lower()

    seed = f"{repository_id.strip()}::{lang_str}::{fp_str}::{fqn_str}::{kind_str}::{scope_index}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return NamespaceID(value=f"ns_{digest}")
