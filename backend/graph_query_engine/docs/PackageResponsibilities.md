# Graph Query Engine Package Responsibilities

| Package | Primary Responsibility | Key Interfaces & Models |
|---|---|---|
| `api/` | Entrypoint query API surface contracts | `IQueryEngineAPI` |
| `budget/` | Resource timeout & memory budget enforcement contracts | `IQueryBudgetManager` |
| `capabilities/` | Feature capability discovery & verification contracts | `ICapabilityRegistry`, `ICapabilityValidator` |
| `config/` | Immutable configuration model, defaults, and env overrides loader | `GraphQueryEngineConfig`, `DefaultConfig`, `ConfigurationLoader`, `ConfigurationValidator` |
| `constants/` | System limits, default timeouts, keywords, and version constants | `ENGINE_NAME`, `ENGINE_VERSION`, `DEFAULT_MAX_TRAVERSAL_DEPTH`, `RESERVED_KEYWORDS` |
| `diagnostics/` | Diagnostics profiling & metric telemetry contracts | `IQueryDiagnostics` |
| `errors/` | Unified error hierarchy with unique codes & stack capture | `GraphQueryError`, `ErrorCode`, `InitializationError`, `ConfigurationError`, `ValidationError`, `ExecutionError`, `TimeoutError`, `NotImplementedError` |
| `extension/` | Engine extension hook contracts | `IQueryExtension` |
| `index/` | Secondary graph index & symbol lookup contracts | `IIndex`, `IIndexRegistry` |
| `lifecycle/` | Engine and component state machine protocols | `EngineState`, `LifecycleState`, `LifecycleComponent`, `LifecycleEvent`, `LifecycleStatus`, `EngineStatus` |
| `logging/` | Structured logging protocols and trace context tracking | `Logger`, `LoggerFactory`, `StructuredLog`, `LogLevel`, `LogContext`, `CorrelationContext` |
| `model/` | Query context and domain query model contracts | `IQueryContext` |
| `pipeline/` | Physical query execution step contracts | `IQueryPipeline`, `IQueryExecutor` |
| `planner/` | Deterministic query optimization & plan contracts | `IQueryPlanner` |
| `shared/` | DI container contracts & common markers | `ServiceRegistry`, `ComponentFactory`, `ComponentProvider`, `Disposable` |
| `traversal/` | Graph traversal strategy protocols | `ITraversalStrategy`, `ITraversalRegistry` |
| `types/` | Strongly-typed domain primitive IDs and enums | `NodeId`, `EdgeId`, `SymbolId`, `FileId`, `TraversalDirection`, `RelationshipType`, `DependencyType` |
| `utils/` | Monadic containers, assertions, and pure helpers | `Result`, `Option`, `Assertions`, `Clock`, `UUIDProvider`, `ImmutableHelper`, `CollectionHelper`, `ValidationHelper`, `PathHelper` |
| `validation/` | Semantic query validation contracts | `IQueryValidator` |
| `view/` | Immutable GraphView read interface contract | `IGraphView` |
