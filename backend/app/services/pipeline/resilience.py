import asyncio
import logging
import time
from typing import Callable, Type

logger = logging.getLogger(__name__)


class CloneError(Exception):
    """Raised when repository cloning fails after all retries."""
    pass


class PipelineError(Exception):
    """Raised when a pipeline stage fails unrecoverably."""
    pass


async def retry_async(
    fn: Callable,
    *,
    attempts: int,
    base_delay: float,
    exc: tuple[Type[Exception], ...] = (Exception,),
    label: str = "",
):
    """
    Retry an async callable with exponential backoff.

    Args:
        fn:         Zero-argument async callable to retry.
        attempts:   Maximum number of attempts (including first).
        base_delay: Seconds to wait after first failure.
                    Second failure waits base_delay * 2, third waits * 4.
        exc:        Exception types to catch and retry on.
                    Any other exception propagates immediately.
        label:      Name shown in log messages for debugging.

    Returns:
        Return value of fn() on success.

    Raises:
        The last exception if all attempts fail.
    """
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except exc as e:
            last_exc = e
            logger.warning(
                "%s attempt %d/%d failed: %s",
                label or "retry_async", attempt, attempts, e
            )
            if attempt < attempts:
                delay = base_delay * (2 ** (attempt - 1))
                logger.info("%s retrying in %.1fs", label or "retry_async", delay)
                await asyncio.sleep(delay)
    raise last_exc


class CircuitBreaker:
    """
    Trips after threshold consecutive failures.
    Blocks all calls for cooldown seconds, then resets.

    Usage:
        cb = CircuitBreaker(threshold=5, cooldown=60.0)
        if cb.allow():
            try:
                await do_thing()
                cb.record(ok=True)
            except Exception:
                cb.record(ok=False)
        else:
            raise PipelineError("Circuit open, skipping call")
    """

    def __init__(self, threshold: int = 5, cooldown: float = 60.0):
        self.threshold = threshold
        self.cooldown = cooldown
        self._failures = 0
        self._opened_at: float = 0.0

    def allow(self) -> bool:
        if self._failures < self.threshold:
            return True
        if (time.monotonic() - self._opened_at) > self.cooldown:
            self._failures = 0
            return True
        return False

    def record(self, ok: bool) -> None:
        if ok:
            self._failures = 0
        else:
            self._failures += 1
            if self._failures == self.threshold:
                self._opened_at = time.monotonic()
                logger.warning(
                    "CircuitBreaker tripped after %d failures", self.threshold
                )
