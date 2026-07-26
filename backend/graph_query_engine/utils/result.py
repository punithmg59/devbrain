"""
Result Monad Utility for Graph Query Engine.
"""

from dataclasses import dataclass
from typing import Callable, Generic, NoReturn, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=Exception)
U = TypeVar("U")


@dataclass(frozen=True)
class Result(Generic[T, E]):
    """
    Immutable monadic Result container representing either success (Ok) or failure (Err).
    """
    _value: T | None
    _error: E | None
    _is_ok: bool

    @classmethod
    def ok(cls, value: T) -> "Result[T, E]":
        """Constructs a successful Result instance."""
        return cls(_value=value, _error=None, _is_ok=True)

    @classmethod
    def err(cls, error: E) -> "Result[T, E]":
        """Constructs a failed Result instance."""
        return cls(_value=None, _error=error, _is_ok=False)

    def is_ok(self) -> bool:
        """Returns True if the result is successful."""
        return self._is_ok

    def is_err(self) -> bool:
        """Returns True if the result is a failure."""
        return not self._is_ok

    def unwrap(self) -> T:
        """
        Returns the contained success value. Raises the contained exception if Err.
        """
        if self._is_ok and self._value is not None:
            return self._value
        if self._error is not None:
            raise self._error
        raise ValueError("Result unwrap called on invalid empty Ok state.")

    def unwrap_or(self, default: T) -> T:
        """
        Returns the contained value if Ok, otherwise returns default value.
        """
        if self._is_ok and self._value is not None:
            return self._value
        return default

    def map(self, fn: Callable[[T], U]) -> "Result[U, E]":
        """
        Applies a mapping function to the contained Ok value.
        """
        if self._is_ok and self._value is not None:
            return Result.ok(fn(self._value))
        assert self._error is not None
        return Result.err(self._error)
