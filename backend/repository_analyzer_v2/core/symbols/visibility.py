"""
core/symbols/visibility.py
--------------------------
Visibility and Accessibility models and utilities.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from core.symbols.enums import AccessibilityKind, VisibilityKind


class Visibility(BaseModel):
    """
    Language-agnostic Visibility specification for a Symbol.
    """
    kind: VisibilityKind = Field(
        default=VisibilityKind.UNKNOWN,
        description="Canonical visibility classification"
    )
    raw_modifier: Optional[str] = Field(
        default=None,
        description="Original language-specific visibility keyword (e.g. 'pub(crate)', 'internal', 'private')"
    )

    model_config = {
        "frozen": True
    }

    @property
    def is_public(self) -> bool:
        return self.kind == VisibilityKind.PUBLIC

    @property
    def is_private(self) -> bool:
        return self.kind == VisibilityKind.PRIVATE

    @property
    def is_protected(self) -> bool:
        return self.kind == VisibilityKind.PROTECTED

    @classmethod
    def public(cls) -> Visibility:
        return cls(kind=VisibilityKind.PUBLIC)

    @classmethod
    def private(cls) -> Visibility:
        return cls(kind=VisibilityKind.PRIVATE)

    @classmethod
    def protected(cls) -> Visibility:
        return cls(kind=VisibilityKind.PROTECTED)

    @classmethod
    def internal(cls) -> Visibility:
        return cls(kind=VisibilityKind.INTERNAL)


class Accessibility(BaseModel):
    """
    Access permissions (read/write/execute) specification for a Symbol.
    """
    kind: AccessibilityKind = Field(
        default=AccessibilityKind.UNKNOWN,
        description="Canonical accessibility classification"
    )

    model_config = {
        "frozen": True
    }

    @classmethod
    def read_only(cls) -> Accessibility:
        return cls(kind=AccessibilityKind.READ_ONLY)

    @classmethod
    def read_write(cls) -> Accessibility:
        return cls(kind=AccessibilityKind.READ_WRITE)
