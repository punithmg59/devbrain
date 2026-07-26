# Coding Standards & Guidelines

## TypeScript Configuration Rules

- **Strict Mode Enabled**: `strict: true`, `noImplicitAny: true`, `strictNullChecks: true`.
- **Strict Checks**: `noUncheckedIndexedAccess: true`, `exactOptionalPropertyTypes: true`, `noImplicitReturns: true`.
- **Module Format**: ES2022 with `NodeNext` resolution (`.js` extension in relative imports).

## Architectural Guidelines

1. **Composition Over Inheritance**: Prefer functional composition, interfaces, and strategy delegation over deep class hierarchies.
2. **Immutable Data Structures**: Mark all configuration objects, errors, and domain descriptors as `Readonly<T>` or `freezeDeep()`.
3. **No Static Global State**: Avoid global singleton objects or mutable static class properties. Pass dependencies via interfaces or constructors.
4. **Branded Nominal Identifiers**: Never pass raw primitive strings where `NodeId`, `QueryId`, or `FileId` is expected. Use the helper factories in `src/types/identifiers.ts`.
5. **Functional Error Handling**: Use `Result<T, E>` or explicit typed error classes (`GraphQueryError`) for failure modes. Do not throw arbitrary strings.
6. **Zero Circular Dependencies**: Strict acyclic dependency graph between modules.
