"""
Unit tests for Shared Utilities (Result, Option, Assertions, Helpers).
"""

import pytest

from graph_query_engine.errors import ValidationError
from graph_query_engine.utils import (
    Assertions,
    Clock,
    CollectionHelper,
    ImmutableHelper,
    Option,
    PathHelper,
    Result,
    UUIDProvider,
    ValidationHelper,
)


def test_result_ok():
    res: Result[int, ValueError] = Result.ok(42)
    assert res.is_ok() is True
    assert res.is_err() is False
    assert res.unwrap() == 42
    assert res.unwrap_or(0) == 42

    mapped = res.map(lambda x: x * 2)
    assert mapped.unwrap() == 84


def test_result_err():
    err = ValueError("failed")
    res: Result[int, ValueError] = Result.err(err)
    assert res.is_ok() is False
    assert res.is_err() is True
    assert res.unwrap_or(100) == 100

    with pytest.raises(ValueError, match="failed"):
        res.unwrap()


def test_option_some():
    opt = Option.some("hello")
    assert opt.is_some() is True
    assert opt.is_none() is False
    assert opt.unwrap() == "hello"
    assert opt.unwrap_or("world") == "hello"

    mapped = opt.map(lambda s: s.upper())
    assert mapped.unwrap() == "HELLO"


def test_option_none():
    opt: Option[str] = Option.none()
    assert opt.is_some() is False
    assert opt.is_none() is True
    assert opt.unwrap_or("default") == "default"

    with pytest.raises(ValueError):
        opt.unwrap()


def test_assertions():
    Assertions.assert_not_null("valid", "param")
    with pytest.raises(ValidationError):
        Assertions.assert_not_null(None, "param")

    Assertions.assert_true(True)
    with pytest.raises(ValidationError):
        Assertions.assert_true(False, "Failed condition")

    Assertions.assert_non_empty([1, 2, 3])
    with pytest.raises(ValidationError):
        Assertions.assert_non_empty([])

    Assertions.assert_positive(5)
    with pytest.raises(ValidationError):
        Assertions.assert_positive(-1)


def test_providers_and_helpers():
    now = Clock.utc_now()
    assert now.year >= 2026

    uuid_str = UUIDProvider.generate_v4()
    assert len(uuid_str) == 36

    prefixed = UUIDProvider.generate_prefixed("query")
    assert prefixed.startswith("query_")

    frozen = ImmutableHelper.freeze_sequence([1, 2, 3])
    assert isinstance(frozen, tuple)

    chunks = CollectionHelper.chunk([1, 2, 3, 4, 5], 2)
    assert chunks == [[1, 2], [3, 4], [5]]

    assert ValidationHelper.is_valid_identifier("valid_id") is True
    assert ValidationHelper.is_valid_identifier("") is False

    assert PathHelper.is_subpath("/a/b", "/a/b/c") is True
