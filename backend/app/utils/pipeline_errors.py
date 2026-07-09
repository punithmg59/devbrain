"""
Pipeline Error Handling — DevBrain AI Pipeline

Provides structured, stage-aware exception handling for the NLQ/AI pipeline.
Full tracebacks are written to the backend log only; the caller receives a
clean, JSON-serialisable payload.

Usage
-----
    async with pipeline_stage("intent_engine", correlation_id) as ctx:
        result = await some_engine.run(...)

    # On failure the context manager raises PipelineStageError.
    # Catch it at the top-level orchestrator and call build_error_response().
"""

from __future__ import annotations

import traceback
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from sqlalchemy.exc import SQLAlchemyError

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# PipelineError payload
# ---------------------------------------------------------------------------

@dataclass
class PipelineError:
    """
    Structured error payload produced when a pipeline stage fails.

    Always JSON-serialisable; never contains raw tracebacks.
    """
    success: bool = False
    stage: str = "unknown"
    error_type: str = "UnknownError"
    message: str = "An unexpected error occurred."
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    recoverable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "stage": self.stage,
            "error_type": self.error_type,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "recoverable": self.recoverable,
        }


# ---------------------------------------------------------------------------
# Internal typed exception (never leaves the backend layer)
# ---------------------------------------------------------------------------

class PipelineStageError(Exception):
    """
    Internal exception raised by pipeline_stage() on failure.
    Carries the full PipelineError payload so the top-level orchestrator
    can convert it to an API response without re-catching every exception type.
    """

    def __init__(self, payload: PipelineError) -> None:
        self.payload = payload
        super().__init__(payload.message)


# ---------------------------------------------------------------------------
# Stage context manager
# ---------------------------------------------------------------------------

@asynccontextmanager
async def pipeline_stage(stage: str, correlation_id: Optional[str] = None):
    """
    Async context manager that wraps a single AI pipeline stage.

    - Logs the full traceback to the backend log only.
    - Raises PipelineStageError with a clean PipelineError payload.
    - Never propagates raw exceptions to the caller.

    Parameters
    ----------
    stage:
        Human-readable stage label (e.g. "intent_engine").
    correlation_id:
        Request-scoped ID for log correlation. Auto-generated when omitted.

    Example
    -------
        async with pipeline_stage("intent_engine", cid):
            intent = engine.classify(request)
    """
    cid = correlation_id or str(uuid.uuid4())
    logger.info(f"[{cid}] Pipeline stage '{stage}' starting")

    try:
        yield
        logger.info(f"[{cid}] Pipeline stage '{stage}' completed")

    # ---- Import / module errors (non-recoverable) -------------------------
    except (ImportError, ModuleNotFoundError) as exc:
        tb = traceback.format_exc()
        logger.error(
            f"[{cid}] [{stage}] ImportError — module={exc.name!r}, "
            f"symbol={_extract_symbol(str(exc))!r}\n"
            f"Expected location: app.services or app.utils\n{tb}"
        )
        raise PipelineStageError(
            PipelineError(
                stage=stage,
                error_type=type(exc).__name__,
                message=(
                    f"A required module could not be loaded in stage '{stage}'. "
                    "Check backend logs for the missing symbol."
                ),
                correlation_id=cid,
                recoverable=False,
            )
        ) from exc

    # ---- SQLAlchemy errors ------------------------------------------------
    except SQLAlchemyError as exc:
        tb = traceback.format_exc()
        logger.error(f"[{cid}] [{stage}] SQLAlchemyError: {exc}\n{tb}")
        raise PipelineStageError(
            PipelineError(
                stage=stage,
                error_type=type(exc).__name__,
                message=(
                    f"A database error occurred in stage '{stage}'. "
                    "The pipeline will degrade gracefully."
                ),
                correlation_id=cid,
                recoverable=True,
            )
        ) from exc

    # ---- Timeout ----------------------------------------------------------
    except TimeoutError as exc:
        tb = traceback.format_exc()
        logger.error(f"[{cid}] [{stage}] TimeoutError: {exc}\n{tb}")
        raise PipelineStageError(
            PipelineError(
                stage=stage,
                error_type="TimeoutError",
                message=f"Stage '{stage}' timed out. Try again or simplify the query.",
                correlation_id=cid,
                recoverable=True,
            )
        ) from exc

    # ---- Validation / value errors (recoverable) -------------------------
    except (ValueError, KeyError) as exc:
        tb = traceback.format_exc()
        logger.error(f"[{cid}] [{stage}] {type(exc).__name__}: {exc}\n{tb}")
        raise PipelineStageError(
            PipelineError(
                stage=stage,
                error_type=type(exc).__name__,
                message=f"Invalid data encountered in stage '{stage}': {exc}",
                correlation_id=cid,
                recoverable=True,
            )
        ) from exc

    # ---- Runtime errors (non-recoverable) --------------------------------
    except RuntimeError as exc:
        tb = traceback.format_exc()
        logger.error(f"[{cid}] [{stage}] RuntimeError: {exc}\n{tb}")
        raise PipelineStageError(
            PipelineError(
                stage=stage,
                error_type="RuntimeError",
                message=(
                    f"A runtime error occurred in stage '{stage}'. "
                    "Contact support if this persists."
                ),
                correlation_id=cid,
                recoverable=False,
            )
        ) from exc

    # ---- Catch-all -------------------------------------------------------
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(
            f"[{cid}] [{stage}] Unexpected {type(exc).__name__}: {exc}\n{tb}"
        )
        raise PipelineStageError(
            PipelineError(
                stage=stage,
                error_type=type(exc).__name__,
                message=f"An unexpected error occurred in stage '{stage}'.",
                correlation_id=cid,
                recoverable=True,
            )
        ) from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_error_response(error: PipelineError) -> Dict[str, Any]:
    """
    Convert a PipelineError into the canonical API error dict.

    Safe to return directly from a FastAPI endpoint as a JSONResponse body.
    Never contains a Python traceback.
    """
    return error.to_dict()


def _extract_symbol(message: str) -> str:
    """Extract the missing symbol name from an ImportError message string."""
    # "cannot import name 'Foo' from 'bar.baz'" → "Foo"
    if "cannot import name" in message:
        parts = message.split("'")
        if len(parts) >= 2:
            return parts[1]
    return message
