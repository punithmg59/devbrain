# Index Lifecycle Documentation

## Purpose
`IndexLifecycle` manages state transitions and history tracking for index construction.

---

## State Machine Diagram

```
CREATED --> BUILDING --> VALIDATING --> READY
  |           |              |
  v           v              v
FAILED      FAILED         FAILED --> DISPOSED
```

## Lifecycle States
1. **`CREATED`**: Index lifecycle instantiated.
2. **`BUILDING`**: Index builder processing `GraphView`.
3. **`VALIDATING`**: `IndexValidator` executing 8 integrity checks.
4. **`READY`**: Index ready for O(1) query lookups.
5. **`FAILED`**: Validation or construction error encountered.
6. **`DISPOSED`**: Index resources marked for disposal.
