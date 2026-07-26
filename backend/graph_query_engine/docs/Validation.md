# GraphView Validation Documentation

## Purpose
`GraphViewValidator` verifies structural, metadata, identity, and snapshot integrity before a `GraphView` is returned by `GraphViewFactory`.

---

## 9 Integrity Categories Checked
1. **Graph Existence**: Rejects null/None instances.
2. **Identity & Metadata**: Validates `GraphIdentity` reference and `schema_version`.
3. **Snapshot Information**: Validates snapshot ID presence.
4. **Node Uniqueness**: Verifies `NodeId` non-emptiness and uniqueness.
5. **Edge Integrity**: Checks `EdgeId` uniqueness and verifies source and target node existence (rejects dangling edges).
6. **Required Metadata**: Ensures `repository_id` is present.
7. **Checksum Integrity**: Validates checksum field presence.
8. **Repository Matching**: Verifies top-level and metadata repository IDs match.
9. **Graph Semver Version**: Ensures semver version is present.

---

## Extensible Validation Hooks (Step 2.1)
`GraphViewValidator` includes placeholder hooks for future validation extensions:
- `_validate_schema_compatibility()`
- `_validate_graph_version_compatibility()`
- `_validate_analyzer_compatibility()`
- `_validate_storage_compatibility()`
- `_validate_capability_hooks()`

---

## Error Handling
If any `ERROR` severity rule fails, `GraphViewFactory` transitions lifecycle state to `FAILED` and raises a `ValidationError` containing the structured `GraphViewValidationReport`.
