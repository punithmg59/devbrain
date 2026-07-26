# Index Diagnostics & Health Reporting

## Purpose
`IndexDiagnostics`, `DiagnosticItem`, `IndexHealthReport`, `IndexPerformanceReport`, and `IndexMemoryReport` provide structured observability into the Index subsystem.

---

## Health Status Codes
- **`HEALTHY`**: All validation rules and consistency checks pass cleanly.
- **`WARNING`**: Non-critical warnings detected (e.g., deprecated index features).
- **`FAILED`**: Integrity or cross-index consistency errors encountered.
