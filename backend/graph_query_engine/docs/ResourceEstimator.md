# Resource Estimator Specification

## Overview
`ResourceEstimator` calculates resource overhead estimates: CPU instruction cycles, memory bytes, temporary object count, and payload size.

---

## Resource Formulae
- CPU Cost: $\text{cardinality} \times \text{cost\_per\_row}$.
- Memory Cost: $\text{cardinality} \times \text{bytes\_per\_row} \times \text{overhead\_multiplier}$.
- Sorting/Deduplication/Grouping: $\mathcal{O}(N \log N)$ CPU cycles.
