# Rule Engine Infrastructure

## Overview

The Rule Engine infrastructure consists of:
- `OptimizationRule`: Abstract base class for rewrite rules.
- `OptimizationRuleContext`: Container carrying plan state, statistics, and diagnostics.
- `OptimizationRuleResult`: Return value of rule applications.
- `OptimizationRuleRegistry`: Thread-safe singleton for rule registration, dependency ordering, and phase scheduling.

```mermaid
classDiagram
    class OptimizationRule {
        +str rule_id
        +str version
        +str category
        +int priority
        +bool enabled
        +can_apply(context) bool*
        +apply(context) OptimizationRuleResult*
    }
    class OptimizationRuleRegistry {
        +register_rule(rule)
        +register_phase(phase)
        +ordered_phases() List~OptimizationPhase~
    }
    OptimizationRuleRegistry "1" o-- "*" OptimizationRule
```
