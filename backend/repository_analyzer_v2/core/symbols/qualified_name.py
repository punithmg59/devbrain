"""
core/symbols/qualified_name.py
------------------------------
Universal QualifiedName Value Object representation.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Union
from pydantic import BaseModel, Field, field_validator

from core.symbols.exceptions import QualifiedNameError


class QualifiedName(BaseModel):
    """
    Language-independent Qualified Name Value Object representing hierarchical symbol names.
    
    Examples:
    - package.module.Class.method
    - app.api.users.get_user
    - com.company.project.service.AuthService.login
    - std::collections::HashMap::insert
    """
    segments: Tuple[str, ...] = Field(
        ...,
        description="Ordered sequence of qualified name identifier segments"
    )
    separator: str = Field(
        default=".",
        description="Canonical delimiter used for string formatting"
    )

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }

    @field_validator("segments", mode="before")
    @classmethod
    def _validate_segments(cls, v: Union[Tuple[str, ...], List[str], str]) -> Tuple[str, ...]:
        if isinstance(v, str):
            v = [s.strip() for s in v.split(".") if s.strip()]
        if not v:
            raise QualifiedNameError("QualifiedName must contain at least one non-empty segment.")
        return tuple(v)

    @field_validator("separator")
    @classmethod
    def _validate_separator(cls, v: str) -> str:
        if not v:
            raise QualifiedNameError("Separator cannot be an empty string.")
        return v

    @classmethod
    def from_string(cls, fqn_str: str, separator: str = ".") -> QualifiedName:
        """Parse a qualified name string using a given delimiter."""
        if not fqn_str or not fqn_str.strip():
            raise QualifiedNameError("Cannot create QualifiedName from empty string.")
        
        # Standardize delimiters if alternative separator used (e.g. '::' or '/')
        clean_str = fqn_str.strip()
        if separator != ".":
            clean_str = clean_str.replace(separator, ".")
            
        segments = [s.strip() for s in clean_str.split(".") if s.strip()]
        if not segments:
            raise QualifiedNameError(f"No valid segments found in qualified name string: '{fqn_str}'")
            
        return cls(segments=tuple(segments), separator=separator)

    @property
    def name(self) -> str:
        """Leaf name identifier (e.g., 'login' in 'AuthService.login')."""
        return self.segments[-1]

    @property
    def parent(self) -> Optional[QualifiedName]:
        """Parent QualifiedName, or None if this is a top-level segment."""
        if len(self.segments) <= 1:
            return None
        return QualifiedName(segments=self.segments[:-1], separator=self.separator)

    @property
    def is_root(self) -> bool:
        """True if this QualifiedName has no parent."""
        return len(self.segments) == 1

    def child(self, child_name: str) -> QualifiedName:
        """Construct a new child QualifiedName appended to this one."""
        if not child_name or not child_name.strip():
            raise QualifiedNameError("Child name cannot be empty.")
        clean_name = child_name.strip()
        return QualifiedName(
            segments=self.segments + (clean_name,),
            separator=self.separator
        )

    def to_string(self, separator: Optional[str] = None) -> str:
        """Render the qualified name as a string using the specified or default separator."""
        sep = separator if separator is not None else self.separator
        return sep.join(self.segments)

    def __str__(self) -> str:
        return self.to_string()

    def __hash__(self) -> int:
        return hash((self.segments, self.separator))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, QualifiedName):
            return self.segments == other.segments
        if isinstance(other, str):
            return str(self) == other
        return False
