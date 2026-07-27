# Optimization Diagnostics

## Overview

`OptimizationDiagnostics` provides thread-safe logging and statistics collection during optimization runs.

It records three categories of events:
- **Applied Rules**: Rules that successfully transformed the plan (`AppliedRuleInfo`).
- **Skipped Rules**: Enabled rules whose `can_apply()` returned False or were disabled (`SkippedRuleInfo`).
- **Rejected Rules**: Rules that threw an exception during evaluation (`RejectedRuleInfo`).
