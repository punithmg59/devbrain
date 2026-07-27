# PlannerCapabilities Documentation

## Purpose
`PlannerCapabilities` provides a capability registry advertising supported planner feature flags (`LOGICAL_PLANNING`, `COST_ESTIMATION`, `OPTIMIZATION`, `PHYSICAL_PLANNING`, `EXECUTION_PLAN`, `GRAPH_DIFF`, `BLAST_RADIUS`, `DISTRIBUTED_PLANNING`).

---

## API Surface
- `is_supported(feature: str | CapabilityFlag) -> bool`: Checks feature support.
- `require_capability(feature: str | CapabilityFlag) -> None`: Raises `CapabilityUnsupportedError` if unsupported.
- `list_capabilities() -> tuple[str, ...]`: Lists all supported capability strings.
