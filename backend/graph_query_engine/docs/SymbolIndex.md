# SymbolIndex Documentation

## Purpose
`SymbolIndex` provides O(1) canonical symbol lookups by `SymbolId`.

---

## API Surface
- `contains(symbol_id: SymbolId | str) -> bool`
- `get(symbol_id: SymbolId | str) -> ImmutableNodeView` (raises `IndexLookupError` if missing)
- `try_get(symbol_id: SymbolId | str) -> Optional[ImmutableNodeView]`
- `symbols() -> tuple[SymbolId, ...]`
- `count() -> int`
