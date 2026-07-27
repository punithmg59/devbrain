# Logical Visitors Specification

## Overview
The Logical Visitor pattern (`graph_query_engine.logical.visitor`) enables external passes (Visualizers, Optimizers, Cost Estimators) to inspect and walk `LogicalPlan` trees cleanly.

---

## Visitor Classes
- `LogicalVisitor`: Protocol interface.
- `BaseLogicalVisitor`: Default depth-first plan tree walker.
- `PrintLogicalVisitor`: Formatted text tree printer.
- `ValidationLogicalVisitor`: Structural validation visitor.
