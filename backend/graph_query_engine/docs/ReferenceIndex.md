# SymbolReferenceIndex Documentation

## Purpose
`SymbolReferenceIndex` maps canonical symbol definition `NodeId`s to tuples of referencing and calling symbol `ImmutableNodeView`s across the codebase.

---

## API Surface
- `references(definition_id: NodeId | str) -> tuple[ImmutableNodeView, ...]`
- `count(definition_id: NodeId | str) -> int`
