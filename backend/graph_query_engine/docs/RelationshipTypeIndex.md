# RelationshipTypeIndex Documentation

## Purpose
`RelationshipTypeIndex` groups graph relationship edges by `RelationshipType` enum (e.g., `CALLS`, `IMPORTS`, `IMPLEMENTS`, `INHERITS`, `REFERENCES`, `USES`, `CONTAINS`, `DEPENDS_ON`).

---

## API Surface
- `relationships(rel_type: RelationshipType | str) -> tuple[ImmutableEdgeView, ...]`
- `count(rel_type: RelationshipType | str) -> int`
- `types() -> tuple[str, ...]`
