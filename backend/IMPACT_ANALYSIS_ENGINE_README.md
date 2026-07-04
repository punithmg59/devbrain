# Impact Analysis Engine

The Impact Analysis Engine provides deterministic engineering impact analysis using graph algorithms, dependency analysis, and repository intelligence. It is designed for repositories with over 100,000 files and does not use LLMs.

## Architecture

### Components

1. **Impact Analysis Schemas** (`app/schemas/impact_analysis.py`)
   - `ImpactAnalysisRequest`: Request schema with intent, repo_id, target, and evidence
   - `ImpactAnalysisResponse`: Response schema with structured engineering data
   - `AffectedEntity`: An entity affected by the change with impact level
   - `BlastRadiusResult`: Blast radius calculation result
   - `ComplexityScore`: Engineering complexity score (0-100)
   - `DifficultyScore`: Difficulty score for implementation/migration
   - `ChangeStep`: A single step in the recommended change order
   - `RiskScore`: Risk score breakdown with factors

2. **GraphTraversal** (`app/services/impact_analysis_engine.py`)
   - `bfs_blast_radius`: BFS algorithm for calculating blast radius
   - `topological_sort`: Topological sort for dependency ordering
   - `find_cyclic_dependencies`: DFS-based cycle detection

3. **RiskScoring** (`app/services/impact_analysis_engine.py`)
   - `calculate_risk_score`: Deterministic risk scoring algorithm
   - Factors: blast radius, dependencies, complexity, workflows, APIs, databases
   - Returns risk category (critical, high, medium, low, safe)

4. **ComplexityScoring** (`app/services/impact_analysis_engine.py`)
   - `calculate_complexity`: Engineering complexity calculation
   - Factors: cyclomatic, dependency, coupling, data, control flow complexity

5. **DifficultyScoring** (`app/services/impact_analysis_engine.py`)
   - `calculate_difficulty`: Implementation and migration difficulty
   - Factors: technical, testing, deployment, migration, rollback difficulty

6. **ChangeOrdering** (`app/services/impact_analysis_engine.py`)
   - `calculate_change_order`: Topological sort-based change ordering
   - Estimates effort based on complexity and impact level

7. **ImpactAnalysisEngine** (`app/services/impact_analysis_engine.py`)
   - Main service orchestrating all analysis components
   - Integrates with repository evidence from Evidence Engine

## Usage

### Basic Usage

```python
from app.services.impact_analysis_engine import ImpactAnalysisEngine
from app.schemas.impact_analysis import ImpactAnalysisRequest
from app.models.intent import Intent
from app.services.repository_evidence_engine import RepositoryEvidenceEngine
from uuid import UUID

# First, collect evidence
evidence_engine = RepositoryEvidenceEngine()
evidence_request = EvidenceRequest(
    intent=Intent.DELETE_CODE,
    repo_id=repo_id,
    target="AuthService"
)
evidence_response = await evidence_engine.collect_evidence(evidence_request, db)

# Then, analyze impact
impact_engine = ImpactAnalysisEngine()
impact_request = ImpactAnalysisRequest(
    intent=Intent.DELETE_CODE,
    repo_id=repo_id,
    target="AuthService",
    evidence=evidence_response,
    max_depth=5,
    include_indirect=True
)

impact_response = await impact_engine.analyze_impact(impact_request, db)

# Access results
print(f"Risk Score: {impact_response.risk_score.overall_risk_score}")
print(f"Risk Category: {impact_response.risk_score.risk_category}")
print(f"Affected Services: {len(impact_response.affected_services)}")
print(f"Total Effort: {impact_response.total_estimated_effort_hours} hours")
```

### Example Output

```python
# Risk assessment
risk_score = impact_response.risk_score
# overall_risk_score: 75.5
# risk_category: "high"
# blast_radius_risk: 80.0
# dependency_risk: 70.0
# complexity_risk: 75.0

# Blast radius
blast_radius = impact_response.blast_radius
# total_affected_entities: 45
# direct_dependencies: 12
# indirect_dependencies: 33

# Affected entities
for service in impact_response.affected_services:
    print(f"{service.name}: {service.impact_level} (distance: {service.dependency_distance})")

# Change order
for step in impact_response.recommended_change_order:
    print(f"Step {step.step_number}: {step.entity_name} ({step.risk_level}) - {step.estimated_effort_hours}h")
```

## Algorithms

### Blast Radius Calculation

Uses **BFS (Breadth-First Search)** to traverse the dependency graph:

1. Start from target node
2. Traverse edges in specified direction (incoming, outgoing, or both)
3. Track distance from target
4. Stop at max_depth
5. Return affected nodes with distances

**Time Complexity**: O(V + E) where V = vertices, E = edges
**Space Complexity**: O(V) for the visited set and queue

### Risk Scoring

Deterministic weighted algorithm:

```
overall_risk = (
    blast_radius_risk * 0.25 +
    dependency_risk * 0.20 +
    complexity_risk * 0.20 +
    workflow_risk * 0.15 +
    api_risk * 0.10 +
    database_risk * 0.10
)

risk_category:
  - critical: >= 80
  - high: >= 60
  - medium: >= 40
  - low: >= 20
  - safe: < 20
```

### Complexity Scoring

Multi-factor complexity calculation:

- **Cyclomatic Complexity**: From node's complexity_score (0-10 scaled to 0-100)
- **Dependency Complexity**: Number of edges * 2
- **Coupling Complexity**: Average degree * 10
- **Data Complexity**: Number of imports * 5
- **Control Flow Complexity**: Number of calls * 3

### Change Ordering

Uses **Topological Sort** for dependency-aware ordering:

1. Build adjacency list from edges
2. Calculate in-degree for each node
3. Initialize queue with nodes having in-degree = 0
4. Process queue, decrementing in-degrees
5. Add nodes with in-degree = 0 to queue
6. Return ordered list

**Time Complexity**: O(V + E)
**Space Complexity**: O(V)

### Cycle Detection

Uses **DFS (Depth-First Search)** with recursion stack:

1. Perform DFS from each unvisited node
2. Track visited nodes and recursion stack
3. If edge to node in recursion stack, cycle found
4. Extract cycle from path

**Time Complexity**: O(V + E)
**Space Complexity**: O(V)

## Performance

Designed for repositories with 100,000+ files:

- **Blast Radius**: ~50-200ms for depth 5 traversal
- **Risk Scoring**: ~1-5ms (deterministic calculation)
- **Complexity Scoring**: ~1-3ms
- **Change Ordering**: ~10-50ms (topological sort)
- **Total Analysis**: ~100-300ms typical

### Scalability Features

- **BFS with max_depth**: Prevents unbounded traversal
- **Efficient data structures**: Uses sets and dicts for O(1) lookups
- **Batch queries**: Fetches nodes in batches
- **Deterministic algorithms**: No LLM calls, predictable performance
- **Async/await**: Non-blocking database operations

## Architecture Decisions

### 1. Deterministic Algorithms Only

**Decision**: Use only deterministic graph algorithms, no LLM.

**Rationale**:
- Predictable results for same input
- Consistent performance regardless of external factors
- No API costs or rate limits
- Explainable and auditable calculations
- Suitable for large-scale repositories (100k+ files)

### 2. Graph Traversal for Blast Radius

**Decision**: Use BFS for blast radius calculation.

**Rationale**:
- BFS naturally explores by distance from target
- Guarantees shortest path distances
- Easy to limit with max_depth
- Efficient for sparse graphs (typical code graphs)
- Well-understood algorithm with O(V+E) complexity

### 3. Weighted Risk Scoring

**Decision**: Use weighted sum of risk factors.

**Rationale**:
- Transparent and explainable
- Easy to tune weights based on domain knowledge
- Deterministic and reproducible
- Each factor contributes meaningfully
- Balances multiple concerns (blast radius, complexity, etc.)

### 4. Topological Sort for Change Ordering

**Decision**: Use topological sort for dependency ordering.

**Rationale**:
- Respects actual dependencies in code
- Prevents circular dependency issues
- Standard algorithm for DAG ordering
- Efficient O(V+E) complexity
- Produces executable change sequence

### 5. Multi-Factor Complexity

**Decision**: Calculate complexity from multiple factors.

**Rationale**:
- Single metric insufficient for code complexity
- Different aspects (cyclomatic, coupling, data) matter
- Weighted combination provides balanced view
- Each factor measurable from graph data
- Aligns with software engineering best practices

### 6. Separate Scoring Classes

**Decision**: Separate classes for Risk, Complexity, Difficulty scoring.

**Rationale**:
- Single responsibility principle
- Easy to test each component independently
- Can modify one without affecting others
- Clear separation of concerns
- Reusable in other contexts

### 7. Strongly Typed Models

**Decision**: Use Pydantic models for all data structures.

**Rationale**:
- Type safety prevents invalid data
- Self-documenting code structure
- Automatic validation at boundaries
- Easy serialization/deserialization
- Clear structure for downstream consumers

### 8. Evidence Integration

**Decision**: Accept optional evidence from Evidence Engine.

**Rationale**:
- Leverages existing repository evidence
- Improves accuracy with pre-collected data
- Optional for flexibility
- Can work standalone if needed
- Integrates with AI Change Intelligence pipeline

### 9. Impact Level Classification

**Decision**: Classify entities by impact level (critical, high, medium, low).

**Rationale**:
- Prioritizes attention to most critical changes
- Helps with change ordering
- Communicates risk clearly
- Based on distance and complexity
- Standard engineering practice

### 10. Effort Estimation

**Decision**: Provide effort estimates in hours.

**Rationale**:
- Actionable for planning
- Based on measurable factors (complexity, impact)
- Helps with resource allocation
- Transparent calculation
- Can be refined with historical data

## Integration with AI Pipeline

The Impact Analysis Engine integrates with the AI Change Intelligence pipeline:

```python
# 1. Classify intent
intent_result = await intent_engine.classify("What breaks if I delete AuthService?")

# 2. Collect evidence
evidence_result = await evidence_engine.collect_evidence(
    EvidenceRequest(
        intent=intent_result.intent,
        repo_id=repo_id,
        target=intent_result.target_name
    ),
    db
)

# 3. Analyze impact
impact_result = await impact_engine.analyze_impact(
    ImpactAnalysisRequest(
        intent=intent_result.intent,
        repo_id=repo_id,
        target=intent_result.target_name,
        evidence=evidence_result
    ),
    db
)

# 4. Generate AI response (with structured context)
ai_response = await ai_agent.generate(
    intent=intent_result,
    evidence=evidence_result,
    impact=impact_result
)
```

## Output Structure

The engine produces structured engineering data:

### Risk Score
- Overall risk score (0-100)
- Risk category (critical, high, medium, low, safe)
- Confidence (0-1)
- Factor breakdown (blast radius, dependencies, complexity, etc.)

### Blast Radius
- Total affected entities
- Direct vs indirect dependencies
- Categorized by type (services, APIs, databases, functions)
- Max depth reached

### Breaking Changes
- Breaking APIs (critical/high impact)
- Breaking services (critical/high impact)
- Breaking databases (critical/high impact)

### Affected Entities
- Services with impact levels
- Databases with impact levels
- Workflows with criticality

### Complexity & Difficulty
- Engineering complexity (0-100)
- Migration difficulty (0-100)
- Implementation difficulty (0-100)
- Factor breakdowns

### Change Plan
- Recommended change order (topological)
- Each step with effort estimate
- Risk level per step
- Dependencies and blocking relationships
- Total estimated effort

## Future Enhancements

Potential improvements:
- Add caching for repeated analyses
- Implement incremental updates for large repos
- Add historical trend analysis
- Include test coverage impact
- Add performance impact estimation
- Support for multi-target analysis
- Real-time impact streaming
- Integration with CI/CD pipelines
- Customizable risk weights per organization
