"""
Option Monad Utility for Graph Query Engine.
"""

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True)
class Option(Generic[T]):
    """
    Immutable monadic Option container representing an optional value (Some or None).
    """
    _value: T | None
    _is_some: bool

    @classmethod
    def some(cls, value: T) -> "Option[T]":
        """Constructs an Option containing a value."""
        return cls(_value=value, _is_some=True)

    @classmethod
    def none(cls) -> "Option[T]":
        """Constructs an empty Option."""
        return cls(_value=None, _is_some=False)

    def is_some(self) -> bool:
        """Returns True if Option contains a value."""
        return self._is_some

    def is_none(self) -> bool:
        """Returns True if Option is empty."""
        return not self._is_some

    def unwrap(self) -> T:
        """
        Returns contained value. Raises ValueError if Option is empty.
        """
        if self._is_some and self._value is not None:
            return self._value
        raise ValueError("Called Option.unwrap() on a None value.")

    def unwrap_or(self, default: T) -> T:
        """
        Returns contained value if Some, otherwise returns default.
        """
        if self._is_some and self._value is not None:
            return self._value
        return default

    def map(self, fn: Callable[[T], U]) -> "Option[U]":
        """
        Applies a mapping function to the contained Some value.
        """
        if self._is_some and self._value is not None:
            return Option.some(fn(self._value))
        return Option.none()
