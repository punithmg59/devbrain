# IndexRegistry Architectural Documentation

## Purpose
`IndexRegistry` provides a thread-safe registry for registering index implementation types and managing active `BaseIndex` instances.

---

## Key Responsibilities
- **Type Registration**: Registers `BaseIndex` subclasses under unique index names.
- **Instance Registration**: Stores validated, active index instances.
- **Thread Safety**: Uses reentrant locks (`threading.RLock`) to ensure concurrency safety during registration and lookup.
- **Provider Integration**: Integrates directly with `IndexProvider` for dependency injection.

---

## Extension Model
Future concrete lookup indexes (Step 3.2: `SymbolIndex`, `FileIndex`, `NamespaceIndex`, `PackageIndex`) register with `IndexRegistry` without modifying core engine source code, adhering to the Open-Closed Principle.
