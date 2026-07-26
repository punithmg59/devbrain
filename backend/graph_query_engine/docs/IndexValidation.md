# Index Validation & Consistency Documentation

## Purpose
`IndexValidationEngine`, `IndexConsistencyChecker`, and `IndexIntegrityChecker` provide centralized validation rules and cross-index consistency checks over all registered index instances.

---

## Key Validation Categories
1. **Structural Integrity**: Non-empty `index_id`, valid `IndexDescriptor.name`, non-empty `snapshot_id`.
2. **Cross-Index Consistency**: Verifies that every edge in `EdgeIndex` references valid, existing source and target `NodeId`s in `NodeIndex`.
3. **Semantic Integrity**: Rejects duplicate API route paths (`METHOD:PATH`) and broken symbol references.
4. **CSR Offset Consistency**: Validates CSR offset bounds and monotonic offset sorting.
