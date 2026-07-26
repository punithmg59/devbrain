# ADR 0004: Strict Layering and Automated Architectural Validation

## Context
Architectural drift occurs when developers bypass layer boundaries (e.g., lower utility layers importing high-level query pipelines).

## Decision
- We define explicit layer hierarchy levels (`types`=10, `errors`=20, `config`=30, `contracts`=50, `view`=60, `traversal`=70, `planner`=80, `pipeline`=90, `core`=100, `api`=110).
- Upward imports (a lower level importing a higher level) are strictly forbidden.
- An automated static AST analyzer (`graph_query_engine.architecture`) is built to enforce these rules in CI.

## Consequences
- **Positive**: Prevents circular dependencies and structural decay automatically during code review.
- **Negative**: Adds automated static analysis checks to CI build runs.

## Alternatives Considered
- **Manual Code Review Only**: Human error eventually permits circular or upward dependencies.

## Future Impact
Guarantees clean architectural layer separation as new features are added over time.
