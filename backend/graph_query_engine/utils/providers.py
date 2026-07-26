"""
Clock and UUID Providers for Graph Query Engine.
"""

from datetime import datetime, timezone
import uuid


class Clock:
    """
    Provider for UTC timestamping.
    """

    @staticmethod
    def utc_now() -> datetime:
        """
        Returns the current UTC datetime.
        """
        return datetime.now(timezone.utc)

    @staticmethod
    def timestamp_seconds() -> float:
        """
        Returns current UTC timestamp in seconds.
        """
        return datetime.now(timezone.utc).timestamp()


class UUIDProvider:
    """
    Provider for generating unique identifiers.
    """

    @staticmethod
    def generate_v4() -> str:
        """
        Generates a standard UUID v4 string.
        """
        return str(uuid.uuid4())

    @staticmethod
    def generate_prefixed(prefix: str) -> str:
        """
        Generates a UUID string formatted with a component prefix.
        """
        return f"{prefix}_{uuid.uuid4().hex[:12]}"
