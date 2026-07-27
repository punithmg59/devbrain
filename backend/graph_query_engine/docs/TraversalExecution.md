# Traversal Execution & Limits

## Overview

The `TraversalEngine` executes graph traversals within explicit safety boundaries defined by `TraversalLimits`:

- `max_depth`: Maximum depth of graph exploration (default 100).
- `max_nodes`: Maximum total nodes visited (default 10,000).
- `max_edges`: Maximum total edges traversed (default 50,000).
- `timeout_ms`: Execution timeout limit (default 30,000 ms).
- `direction`: Default edge direction (`OUTGOING`, `INCOMING`, `BOTH`).

```mermaid
stateDiagram-v2
    [*] --> StartTraversal
    StartTraversal --> CheckLimits
    CheckLimits --> ExpandFrontier: Within Limits
    CheckLimits --> PruneAndTerminate: Limits Reached
    ExpandFrontier --> DetectCycles: Check Back Edges
    DetectCycles --> ExpandFrontier: Next Depth Step
    ExpandFrontier --> AssembleResult: Exploration Complete
    PruneAndTerminate --> AssembleResult
    AssembleResult --> [*]
```
