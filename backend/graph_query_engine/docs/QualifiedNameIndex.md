# QualifiedNameIndex Documentation

## Purpose
`QualifiedNameIndex` provides exact, case-sensitive O(1) lookups by fully qualified symbol strings (e.g. `app.services.auth.login`).

---

## API Surface
- `contains(qualified_name: str) -> bool`
- `get(qualified_name: str) -> ImmutableNodeView` (raises `IndexLookupError` if missing)
- `try_get(qualified_name: str) -> Optional[ImmutableNodeView]`
- `names() -> tuple[str, ...]`
- `count() -> int`
