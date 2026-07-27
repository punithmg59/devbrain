# PlannerMetrics Documentation

## Purpose
`PlannerMetrics` and `MetricsCollector` aggregate operational telemetry metrics (planning time, stage duration, optimization counts, validation counts, errors, warnings) for Prometheus integration.

---

## Metric Attributes
- `planning_time_seconds`: Total planning duration in seconds.
- `stage_durations_ms`: Dict mapping stage names to duration in milliseconds.
- `optimization_count`: Total optimization passes.
- `validation_count`: Total validation passes.
- `warning_count`: Total warnings recorded.
- `error_count`: Total errors recorded.
