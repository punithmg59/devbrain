# Selectivity Estimator Specification

## Overview
`SelectivityEstimator` calculates predicate filter selectivity factors ($0.0 \le s \le 1.0$).

---

## Predicate Selectivities
- `EqualityPredicate` on Primary Key: $s = 0.001$.
- `EqualityPredicate` on General Attributes: $s = 0.05$.
- `RangePredicate`: $s = 0.25$.
- `ContainsPredicate`: $s = 0.15$.
- `AndPredicate`: $s = s_1 \times s_2 \times \dots$.
- `OrPredicate`: $s = 1 - (1 - s_1)(1 - s_2)\dots$.
