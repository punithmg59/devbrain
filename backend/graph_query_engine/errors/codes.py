"""
Graph Query Engine Error Codes.
"""

from enum import StrEnum, auto


class ErrorCode(StrEnum):
    """Enumeration of all error codes across Graph Query Engine layers."""

    GENERIC_ERROR = "ERR_GQE_000"
    CONFIGURATION_INVALID = auto()
    VALIDATION_FAILED = auto()
    EXECUTION_FAILED = auto()
    TIMEOUT_EXCEEDED = auto()
    NOT_IMPLEMENTED = auto()

    # --- Step 1 Error Codes ---
    CONFIG_INVALID = auto()
    CONFIG_NOT_FOUND = auto()
    CONFIG_TYPE_ERROR = auto()
    INITIALIZATION_FAILED = auto()
    SHUTDOWN_FAILED = auto()
    INVALID_STATE_TRANSITION = auto()
    ALREADY_INITIALIZED = auto()
    NOT_INITIALIZED = auto()
    GRAPH_NOT_LOADED = auto()
    GRAPH_EMPTY = auto()
    NODE_NOT_FOUND = auto()
    EDGE_NOT_FOUND = auto()

    # --- Step 2 Error Codes ---
    INVALID_VIEW_STATE = auto()
    IMMUTABILITY_VIOLATION = auto()
    SNAPSHOT_NOT_FOUND = auto()
    SNAPSHOT_CORRUPTED = auto()
    SNAPSHOT_MISMATCH = auto()
    GRAPH_IDENTITY_MISMATCH = auto()
    ADAPTER_MAPPING_ERROR = auto()

    # --- Step 3.2 Error Codes ---
    DUPLICATE_NODE = auto()
    DUPLICATE_EDGE = auto()
    DUPLICATE_SYMBOL = auto()
    DUPLICATE_QUALIFIED_NAME = auto()
    INDEX_BUILD_ERROR = auto()
    INDEX_LOOKUP_ERROR = auto()

    # --- Step 3.3 Error Codes ---
    INVALID_RELATIONSHIP = auto()
    DANGLING_EDGE = auto()
    RELATIONSHIP_INTEGRITY_ERROR = auto()
    CSR_CONSTRUCTION_ERROR = auto()
    RELATIONSHIP_LOOKUP_ERROR = auto()

    # --- Step 3.4 Error Codes ---
    SEMANTIC_INDEX_ERROR = auto()
    INVALID_INHERITANCE = auto()
    DUPLICATE_ROUTE = auto()
    BROKEN_REFERENCE = auto()
    INVALID_IMPORT = auto()
    INVALID_ANNOTATION = auto()
    MISSING_INTERFACE = auto()
    MISSING_PARENT_TYPE = auto()
    DUPLICATE_DEFINITION = auto()

    # --- Step 4.1 Error Codes ---
    PLANNER_ERROR = auto()
    INVALID_PLANNER_STATE = auto()
    BUDGET_EXCEEDED = auto()
    INVALID_PLANNER_CONFIG = auto()
    PLANNER_REGISTRY_ERROR = auto()
    CAPABILITY_UNSUPPORTED = auto()
    PLANNER_CONTEXT_ERROR = auto()


__all__ = ["ErrorCode"]
