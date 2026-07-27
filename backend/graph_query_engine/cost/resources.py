"""
Resource Estimator Engine.

Estimates CPU work units, memory bytes overhead, temporary object counts, and payload byte sizes.
"""

from typing import Tuple
from pydantic import BaseModel, ConfigDict, Field


class ResourceRequirement(BaseModel):
    """
    Immutable resource requirement estimate model.
    """
    model_config = ConfigDict(frozen=True)

    cpu_cycles: float = Field(default=10.0, ge=0.0, description="Estimated CPU cycles or instruction units")
    memory_bytes: float = Field(default=1024.0, ge=0.0, description="Estimated RAM memory bytes overhead")
    temp_objects_count: float = Field(default=1.0, ge=0.0, description="Estimated temporary objects created")
    payload_size_bytes: float = Field(default=512.0, ge=0.0, description="Estimated output payload bytes")


class ResourceEstimator:
    """
    Pure functional resource estimator for logical operations.
    """

    @classmethod
    def estimate_operator_resources(
        cls,
        operator_name: str,
        estimated_cardinality: float,
        output_schema_size: int = 4,
    ) -> ResourceRequirement:
        """
        Estimates CPU cycles, memory, and payload size based on operator name and cardinality.
        """
        card = max(estimated_cardinality, 1.0)
        bytes_per_row = max(output_schema_size, 1) * 128.0

        if operator_name == "LOGICAL_LOOKUP":
            return ResourceRequirement(
                cpu_cycles=10.0,
                memory_bytes=1024.0,
                temp_objects_count=2.0,
                payload_size_bytes=bytes_per_row,
            )

        elif operator_name == "LOGICAL_EXPAND":
            return ResourceRequirement(
                cpu_cycles=card * 15.0,
                memory_bytes=card * bytes_per_row * 1.5,
                temp_objects_count=card * 2.0,
                payload_size_bytes=card * bytes_per_row,
            )

        elif operator_name == "LOGICAL_FILTER":
            return ResourceRequirement(
                cpu_cycles=card * 5.0,
                memory_bytes=card * 32.0,
                temp_objects_count=card * 0.1,
                payload_size_bytes=card * bytes_per_row,
            )

        elif operator_name == "LOGICAL_PROJECTION":
            return ResourceRequirement(
                cpu_cycles=card * 2.0,
                memory_bytes=card * bytes_per_row,
                temp_objects_count=card * 0.5,
                payload_size_bytes=card * bytes_per_row,
            )

        elif operator_name in ("LOGICAL_SORTING", "LOGICAL_DEDUPLICATION", "LOGICAL_GROUPING"):
            import math
            log_c = math.log2(card) if card > 1 else 1.0
            return ResourceRequirement(
                cpu_cycles=card * log_c * 10.0,
                memory_bytes=card * bytes_per_row * 2.0,
                temp_objects_count=card * 1.0,
                payload_size_bytes=card * bytes_per_row,
            )

        elif operator_name == "LOGICAL_JOIN":
            return ResourceRequirement(
                cpu_cycles=card * 25.0,
                memory_bytes=card * bytes_per_row * 3.0,
                temp_objects_count=card * 2.0,
                payload_size_bytes=card * bytes_per_row,
            )

        return ResourceRequirement(
            cpu_cycles=card * 5.0,
            memory_bytes=card * bytes_per_row,
            temp_objects_count=card,
            payload_size_bytes=card * bytes_per_row,
        )


__all__ = [
    "ResourceRequirement",
    "ResourceEstimator",
]
