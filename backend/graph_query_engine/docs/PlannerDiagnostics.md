# PlannerDiagnostics Documentation

## Purpose
`PlannerDiagnostics` provides thread-safe collection of diagnostic events, stage timings, warnings, errors, and trace messages across planning pipeline stages.

---

## Event Levels
- `INFO`: Informational events.
- `WARNING`: Planning warnings.
- `ERROR`: Planning stage failures.
- `STAGE_START`: Pipeline stage start timestamp.
- `STAGE_END`: Pipeline stage completion timestamp.
- `TIMING`: Microsecond stage duration logs.
