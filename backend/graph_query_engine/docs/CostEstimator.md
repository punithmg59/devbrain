# CostEstimator Specification

## Overview
`CostEstimator` is the primary orchestrator of Step 4.4.

---

## Workflow Sequence
1. Consumes a `LogicalPlan` and optional `GraphStatisticsMetadata`.
2. Invokes `BaseCostVisitor` to walk the operator tree bottom-up.
3. Invokes operator-specific cost estimators (`LookupCostEstimator`, `ExpandCostEstimator`, `FilterCostEstimator`, etc.).
4. Aggregates operator estimates into a cumulative plan cost using `CostAggregator`.
5. Validates non-negative costs and confidence score bounds using `CostValidator`.
6. Produces the canonical `CostReport`.
