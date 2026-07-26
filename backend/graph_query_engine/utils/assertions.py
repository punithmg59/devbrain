"""
Assertions Utility for Graph Query Engine.
"""

from typing import Any, Collection, TypeVar

from graph_query_engine.errors import ValidationError

T = TypeVar("T")


class Assertions:
    """
    Defensive programming assertion helpers for parameter validation.
    """

    @staticmethod
    def assert_not_null(
        value: Any,
        param_name: str = "parameter",
    ) -> None:
        """
        Ensures the provided value is not None.
        """
        if value is None:
            raise ValidationError(f"Parameter '{param_name}' must not be null/None.")

    @staticmethod
    def assert_true(
        condition: bool,
        message: str = "Assertion failed.",
    ) -> None:
        """
        Ensures the provided boolean condition evaluates to True.
        """
        if not condition:
            raise ValidationError(message)

    @staticmethod
    def assert_non_empty(
        value: Collection[Any] | str,
        param_name: str = "collection",
    ) -> None:
        """
        Ensures the collection or string is not empty.
        """
        if value is None or len(value) == 0:
            raise ValidationError(f"Parameter '{param_name}' must not be empty.")

    @staticmethod
    def assert_positive(
        value: int | float,
        param_name: str = "number",
    ) -> None:
        """
        Ensures a numeric value is strictly greater than zero.
        """
        if value <= 0:
            raise ValidationError(f"Parameter '{param_name}' must be positive (> 0).")
