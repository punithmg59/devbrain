"""
Capabilities Interface Contracts.

CONTRACT ONLY - DO NOT IMPLEMENT IN STEP 1.1.
"""

from typing import Protocol


class ICapabilityRegistry(Protocol):
    """
    Contract for discovering engine capabilities and features.
    """

    def has_capability(self, capability_name: str) -> bool:
        """Checks if a capability is supported by engine."""
        ...


class ICapabilityValidator(Protocol):
    """
    Contract for validating if a query requires supported capabilities.
    """

    def validate_capabilities(self, query_ast: str) -> None:
        """Validates query capability requirements."""
        ...


__all__ = ["ICapabilityRegistry", "ICapabilityValidator"]
