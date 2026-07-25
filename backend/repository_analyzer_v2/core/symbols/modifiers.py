"""
core/symbols/modifiers.py
-------------------------
Language-independent Modifier model and query utilities.
"""

from __future__ import annotations

from typing import FrozenSet, Iterable, Set, Union
from pydantic import BaseModel, Field, field_validator

from core.symbols.enums import ModifierKind


class ModifierSet(BaseModel):
    """
    Immutable container representing a set of language-independent symbol modifiers.
    """
    modifiers: FrozenSet[ModifierKind] = Field(
        default_factory=frozenset,
        description="Immutable set of modifier kinds"
    )

    model_config = {
        "frozen": True
    }

    @field_validator("modifiers", mode="before")
    @classmethod
    def _validate_modifiers(cls, v: Union[Iterable[Union[ModifierKind, str]], None]) -> FrozenSet[ModifierKind]:
        if v is None:
            return frozenset()
        result: Set[ModifierKind] = set()
        for item in v:
            if isinstance(item, ModifierKind):
                result.add(item)
            elif isinstance(item, str):
                try:
                    result.add(ModifierKind(item.lower()))
                except ValueError:
                    pass
        return frozenset(result)

    def has(self, modifier: Union[ModifierKind, str]) -> bool:
        if isinstance(modifier, ModifierKind):
            return modifier in self.modifiers
        try:
            return ModifierKind(modifier.lower()) in self.modifiers
        except ValueError:
            return False

    @property
    def is_static(self) -> bool:
        return ModifierKind.STATIC in self.modifiers

    @property
    def is_abstract(self) -> bool:
        return ModifierKind.ABSTRACT in self.modifiers

    @property
    def is_async(self) -> bool:
        return ModifierKind.ASYNC in self.modifiers

    @property
    def is_final(self) -> bool:
        return ModifierKind.FINAL in self.modifiers

    @property
    def is_readonly(self) -> bool:
        return ModifierKind.READONLY in self.modifiers

    @property
    def is_deprecated(self) -> bool:
        return ModifierKind.DEPRECATED in self.modifiers

    @property
    def is_const(self) -> bool:
        return ModifierKind.CONST in self.modifiers

    @property
    def is_override(self) -> bool:
        return ModifierKind.OVERRIDE in self.modifiers

    @property
    def is_virtual(self) -> bool:
        return ModifierKind.VIRTUAL in self.modifiers

    @property
    def is_sealed(self) -> bool:
        return ModifierKind.SEALED in self.modifiers

    def with_modifier(self, modifier: ModifierKind) -> ModifierSet:
        """Return a new ModifierSet with the added modifier."""
        return ModifierSet(modifiers=self.modifiers | {modifier})

    def without_modifier(self, modifier: ModifierKind) -> ModifierSet:
        """Return a new ModifierSet without the specified modifier."""
        return ModifierSet(modifiers=self.modifiers - {modifier})
