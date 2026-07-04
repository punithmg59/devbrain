# Recommendation Engine

The Recommendation Engine provides deterministic engineering recommendations using rule-based algorithms and dependency analysis. It generates actionable recommendations without using LLMs, designed to support future Root Cause Intelligence.

## Architecture

### Components

1. **Recommendation Schemas** (`app/schemas/recommendation.py`)
   - `RecommendationRequest`: Request schema with intent, evidence, and impact
   - `RecommendationResponse`: Response schema with all recommendations
   - `Recommendation`: A single recommendation with priority and effort
   - `DeleteOrderRecommendation`: Specific recommendation for delete order
   - `RefactorRecommendation`: Refactoring recommendation with complexity targets
   - `TestRecommendation`: Test recommendation with coverage targets
   - `WorkflowRecommendation`: Workflow review/update recommendation
   - `MigrationRecommendation`: Database migration recommendation
   - `RollbackStep`: A single step in a rollback plan
   - `RollbackPlan`: Complete rollback plan with automation info

2. **DeleteOrderGenerator** (`app/services/recommendation_engine.py`)
   - Generates delete order based on dependency graph
   - Strategy: Delete leaf nodes first (no dependents), then work inward
   - Uses reverse of change order for safe deletion sequence

3. **RefactorRecommendationGenerator** (`app/services/recommendation_engine.py`)
   - Generates refactoring recommendations based on complexity
   - Strategy: Recommend refactoring for high-complexity entities
   - Types: extract_method, simplify, rename based on complexity level

4. **TestRecommendationGenerator** (`app/services/recommendation_engine.py`)
   - Generates test recommendations based on affected entities
   - Strategy: Recommend tests for high-impact entities and critical paths
   - Types: unit, integration, e2e based on entity type

5. **WorkflowRecommendationGenerator** (`app/services/recommendation_engine.py`)
   - Generates workflow review recommendations
   - Strategy: Review workflows that include affected services or APIs
   - Actions: update (if affected) or review (if potentially affected)

6. **MigrationRecommendationGenerator** (`app/services/recommendation_engine.py`)
   - Generates database migration recommendations
   - Strategy: Generate appropriate migrations based on intent
   - Types: create_table, alter_table, drop_table based on operation

7. **RollbackPlanGenerator** (`app/services/recommendation_engine.py`)
   - Generates rollback plan based on change steps
   - Strategy: Reverse the change order for rollback
   - Includes database rollback steps and automation assessment

8. **RecommendationEngine** (`app/services/recommendation_engine.py`)
   - Main service orchestrating all recommendation generators
   - Integrates with Evidence Engine and Impact Analysis Engine
   - Prioritizes and aggregates all recommendations

## Usage

### Basic Usage

```python
from app.services.recommendation_engine import RecommendationEngine
from app.schemas.recommendation import RecommendationRequest
from app.models.intent import Intent
from app.services.repository_evidence_engine import RepositoryEvidenceEngine
from app.services.impact_analysis_engine import ImpactAnalysisEngine
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
    evidence=evidence_response
)
impact_response = await impact_engine.analyze_impact(impact_request, db)

# Finally, generate recommendations
recommendation_engine = RecommendationEngine()
recommendation_request = RecommendationRequest(
    intent=Intent.DELETE_CODE,
    repo_id=repo_id,
    target="AuthService",
    evidence=evidence_response,
    impact=impact_response,
    include_rollback=True,
    include_tests=True
)

recommendation_response = recommendation_engine.generate_recommendations(recommendation_request)

# Access results
print(f"Total Recommendations: {recommendation_response.total_recommendations}")
print(f"Critical: {recommendation_response.critical_count}")
print(f"High: {recommendation_response.high_count}")
print(f"Total Effort: {recommendation_response.total_estimated_effort_hours} hours")
```

### Example Output

```python
# Delete order
for rec in recommendation_response.delete_order:
    print(f"Step {rec.step_number}: Delete {rec.entity_name}")
    print(f"  Reason: {rec.reason}")
    print(f"  Safe: {rec.safe_to_delete}")
    print(f"  Rollback: {rec.rollback_action}")

# Refactor recommendations
for rec in recommendation_response.refactor_recommendations:
    print(f"Refactor {rec.file_path}")
    print(f"  Type: {rec.refactor_type}")
    print(f"  Complexity: {rec.current_complexity} -> {rec.target_complexity}")

# Test recommendations
for rec in recommendation_response.test_recommendations:
    print(f"Test {rec.target_entity_name}")
    print(f"  Type: {rec.test_type}")
    print(f"  Coverage: {rec.coverage_target}")

# Rollback plan
if recommendation_response.rollback_plan:
    print(f"Rollback Plan: {recommendation_response.rollback_plan.total_steps} steps")
    print(f"  Can automate: {recommendation_response.rollback_plan.can_rollback_automatically}")
    print(f"  Data loss risk: {recommendation_response.rollback_plan.data_loss_risk}")
```

## Algorithms

### Delete Order Generation

Uses **dependency graph analysis** to determine safe deletion order:

1. Build dependency graph from change steps
2. Map entities to their dependents
3. Identify leaf nodes (entities with no dependents)
4. Delete leaf nodes first, then work inward
5. Reverse the change order for deletion sequence

**Strategy**: Delete entities that nothing depends on first to minimize breaking changes.

### Refactoring Recommendations

Uses **complexity threshold analysis**:

- **High complexity (>70)**: extract_method (reduce by 40%)
- **Medium complexity (>50)**: simplify (reduce by 20%)
- **Low complexity (<50)**: rename (for clarity)

**Strategy**: Focus on high-impact, high-complexity entities first.

### Test Recommendations

Uses **entity type and impact level**:

- **Services**: integration tests, 80% coverage
- **API routes**: integration tests, 90% coverage
- **Functions**: unit tests, 95% coverage
- **Models**: integration tests, 85% coverage

**Strategy**: Prioritize critical and high-impact entities.

### Workflow Recommendations

Uses **string matching** on workflow names:

- If workflow name contains affected service/API: update
- Otherwise: review

**Strategy**: Directly affected workflows need updates, others need review.

### Migration Recommendations

Uses **intent-based mapping**:

- **DELETE_CODE**: drop_table (destructive, requires downtime)
- **MODIFY_CODE**: alter_table (non-destructive)
- **ADD_FEATURE**: create_table (non-destructive)

**Strategy**: Generate appropriate migration type for each intent.

### Rollback Plan Generation

Uses **reverse change order**:

1. Reverse the change steps for rollback sequence
2. Add database rollback steps if needed
3. Calculate total time and automation feasibility
4. Assess data loss risk based on impact levels

**Strategy**: Rollback should reverse the exact change sequence.

## Architecture Decisions

### 1. Deterministic Rule-Based Algorithms

**Decision**: Use only deterministic rule-based algorithms, no LLM.

**Rationale**:
- Predictable results for same input
- No hallucinations or inconsistent recommendations
- No API costs or rate limits
- Explainable and auditable logic
- Suitable for Root Cause Intelligence (future)

### 2. Dependency-Based Delete Order

**Decision**: Use dependency graph analysis for delete order.

**Rationale**:
- Ensures safe deletion sequence
- Prevents breaking dependencies
- Minimizes cascading failures
- Standard engineering practice
- Leverages existing change order from Impact Analysis

### 3. Complexity-Driven Refactoring

**Decision**: Base refactoring recommendations on complexity scores.

**Rationale**:
- High complexity indicates technical debt
- Quantifiable metric for prioritization
- Clear before/after targets
- Aligns with software engineering best practices
- Actionable and measurable

### 4. Impact-Based Test Prioritization

**Decision**: Prioritize tests based on impact level and entity type.

**Rationale**:
- Critical components need comprehensive testing
- Different entity types require different test strategies
- Efficient resource allocation
- Reduces risk of regressions
- Standard testing methodology

### 5. Intent-Based Migration Generation

**Decision**: Map intents to specific migration types.

**Rationale**:
- Clear mapping between operation and migration
- Prevents inappropriate migration types
- Includes destructive/non-destructive classification
- Includes downtime requirements
- Includes rollback SQL

### 6. Reverse Order Rollback

**Decision**: Use reverse change order for rollback plan.

**Rationale**:
- Logical reversal of changes
- Ensures dependencies are restored correctly
- Standard rollback practice
- Easy to verify
- Includes automation feasibility assessment

### 7. Separate Generator Classes

**Decision**: Separate classes for each recommendation type.

**Rationale**:
- Single responsibility principle
- Easy to test each generator independently
- Can modify one without affecting others
- Clear separation of concerns
- Reusable in other contexts

### 8. Strongly Typed Models

**Decision**: Use Pydantic models for all recommendation structures.

**Rationale**:
- Type safety prevents invalid recommendations
- Self-documenting code structure
- Automatic validation at boundaries
- Easy serialization to JSON
- Clear structure for downstream consumers

### 9. Priority-Based Ordering

**Decision**: Order recommendations by priority (critical, high, medium, low).

**Rationale**:
- Guides attention to most important changes
- Helps with resource allocation
- Standard engineering practice
- Clear communication of urgency
- Actionable prioritization

### 10. Effort Estimation

**Decision**: Provide effort estimates in hours for each recommendation.

**Rationale**:
- Actionable for planning
- Based on measurable factors (complexity, impact)
- Helps with resource allocation
- Transparent calculation
- Can be refined with historical data

## Integration with AI Pipeline

The Recommendation Engine integrates with the AI Change Intelligence pipeline:

```python
# 1. Classify intent
intent_result = await intent_engine.classify("What breaks if I delete AuthService?")

# 2. Collect evidence
evidence_result = await evidence_engine.collect_evidence(
    EvidenceRequest(intent=intent_result.intent, repo_id=repo_id, target=intent_result.target_name),
    db
)

# 3. Analyze impact
impact_result = await impact_engine.analyze_impact(
    ImpactAnalysisRequest(intent=intent_result.intent, repo_id=repo_id, target=intent_result.target_name, evidence=evidence_result),
    db
)

# 4. Generate recommendations
recommendation_result = recommendation_engine.generate_recommendations(
    RecommendationRequest(
        intent=intent_result.intent,
        repo_id=repo_id,
        target=intent_result.target_name,
        evidence=evidence_result,
        impact=impact_result
    )
)

# 5. Generate AI response (with structured recommendations)
ai_response = await ai_agent.generate(
    intent=intent_result,
    evidence=evidence_result,
    impact=impact_result,
    recommendations=recommendation_result
)
```

## Output Structure

The engine produces structured engineering recommendations:

### Delete Order
- Step-by-step deletion sequence
- Safety assessment per entity
- Rollback actions per entity
- Blocking relationships

### Refactor Recommendations
- File path to refactor
- Refactor type (extract_method, simplify, rename)
- Current and target complexity
- Estimated lines changed
- Reason for refactoring

### Test Recommendations
- Test type (unit, integration, e2e)
- Target entity and framework
- Coverage target
- Priority and reason

### Workflow Recommendations
- Workflow to review/update
- Action (review or update)
- Reason and affected components

### Migration Recommendations
- Migration type (create, alter, drop)
- Table name and description
- Destructive/downtime flags
- Rollback SQL

### Rollback Plan
- Total steps and estimated time
- Automation feasibility
- Manual intervention requirement
- Data loss risk assessment
- Step-by-step rollback instructions

## Future Root Cause Intelligence Support

The engine is designed to support future Root Cause Intelligence:

1. **Deterministic Logic**: No LLM hallucinations, reliable for root cause analysis
2. **Structured Output**: JSON format suitable for automated analysis
3. **Dependency Tracking**: Maintains dependency relationships for causal analysis
4. **Impact Assessment**: Provides impact levels for severity classification
5. **Rollback Plans**: Supports recovery planning for incident response
6. **Test Coverage**: Identifies test gaps that may have contributed to issues
7. **Workflow Context**: Provides workflow context for understanding system behavior

## Performance

- **Delete Order Generation**: ~5-10ms
- **Refactor Recommendations**: ~5-10ms
- **Test Recommendations**: ~5-10ms
- **Workflow Recommendations**: ~5-10ms
- **Migration Recommendations**: ~5-10ms
- **Rollback Plan Generation**: ~5-10ms
- **Total Generation**: ~30-60ms typical

## Future Enhancements

Potential improvements:
- Add historical data for better effort estimation
- Include test coverage analysis
- Add performance impact recommendations
- Support for multi-target recommendations
- Integration with CI/CD for automated execution
- Customizable recommendation rules per organization
- Machine learning for effort estimation refinement
- Integration with monitoring for rollback verification
