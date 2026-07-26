# ADR 0006: Extension Points and Capabilities Contracts

## Context
Future query algorithms, user-defined traversal functions, and custom indexes must be plugin-extensible without modifying core engine source code.

## Decision
- We define `IQueryExtension`, `ICapabilityRegistry`, `ICapabilityValidator`, `ITraversalRegistry`, and `IIndexRegistry` as explicit extension point contracts.
- Custom algorithms or indexes plug into the engine via these registry protocols.

## Consequences
- **Positive**: Adheres to Open-Closed Principle (Open for extension, Closed for modification).
- **Negative**: Adds interface indirection for extension lookup.

## Alternatives Considered
- **Hardcoding Traversal Algorithms**: Prevents adding specialized domain traversals later.

## Future Impact
Allows enterprise teams to register custom domain graph traversal routines seamlessly.
