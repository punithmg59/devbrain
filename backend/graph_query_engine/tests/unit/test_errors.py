"""
Unit tests for Error Framework.
"""

from datetime import datetime, timezone
import pytest

from graph_query_engine.errors import (
    ConfigurationError,
    ErrorCode,
    ExecutionError,
    GraphQueryError,
    InitializationError,
    NotImplementedError,
    TimeoutError,
    ValidationError,
)


def test_base_graph_query_error():
    cause = ValueError("root cause")
    error = GraphQueryError(
        message="An error occurred",
        code=ErrorCode.GENERIC_ERROR,
        metadata={"key": "val"},
        cause=cause,
    )

    assert error.message == "An error occurred"
    assert error.code == ErrorCode.GENERIC_ERROR
    assert error.metadata == {"key": "val"}
    assert error.cause is cause
    assert isinstance(error.timestamp, datetime)
    assert len(error.stack_trace) > 0

    err_dict = error.to_dict()
    assert err_dict["code"] == "ERR_GQE_000"
    assert err_dict["message"] == "An error occurred"
    assert err_dict["metadata"] == {"key": "val"}
    assert "root cause" in err_dict["cause"]


def test_error_subclasses():
    init_err = InitializationError("Init failed")
    assert init_err.code == ErrorCode.INITIALIZATION_FAILED

    cfg_err = ConfigurationError("Config invalid")
    assert cfg_err.code == ErrorCode.CONFIGURATION_INVALID

    val_err = ValidationError("Validation invalid")
    assert val_err.code == ErrorCode.VALIDATION_FAILED

    exec_err = ExecutionError("Exec failed")
    assert exec_err.code == ErrorCode.EXECUTION_FAILED

    to_err = TimeoutError("Timeout exceeded")
    assert to_err.code == ErrorCode.TIMEOUT_EXCEEDED

    not_impl_err = NotImplementedError("Not implemented")
    assert not_impl_err.code == ErrorCode.NOT_IMPLEMENTED
