# Graph Query Engine Coding Standards

## Target Environment
- **Python**: 3.12+
- **Style Enforcement**: Standard PEP 8, Ruff compatible, Black formatted.
- **Type Checking**: Full type annotations (`mypy` strict mode compatible).

## Guidelines

1. **Immutability & Value Objects**:
   - Use `typing.NewType` or `frozen=True` dataclasses / Pydantic v2 models for domain data.
   - Prevent state mutations after object initialization.

2. **Error Handling**:
   - Raise exceptions inherited from `GraphQueryError`.
   - Always supply explicit `ErrorCode`, descriptive message, and relevant `metadata`.
   - Prefer monadic `Result[T, E]` or `Option[T]` return types for expected optional/fallible operations.

3. **Contracts Over Implementation**:
   - Declare interfaces using `typing.Protocol`.
   - Avoid hard coupling to concrete classes.
   - Rely on dependency injection contracts (`ServiceRegistry`, `ComponentProvider`).

4. **No Global State**:
   - Do not instantiate global mutable variables, singletons, or global registries.
   - Pass configuration and contexts explicitly.

5. **Docstrings**:
   - Complete Google/Sphinx style module and class docstrings for every public element.
