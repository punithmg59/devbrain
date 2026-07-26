# AnnotationIndex Documentation

## Purpose
`AnnotationIndex` groups symbols by decorator or annotation string (e.g. `@app.get`, `@dataclass`, `@Controller`, `@Service`, `@Entity`, `@Inject`, `@staticmethod`, `@classmethod`).

---

## API Surface
- `by_annotation(annotation: str) -> tuple[ImmutableNodeView, ...]`
- `annotations() -> tuple[str, ...]`
- `count(annotation: str) -> int`
