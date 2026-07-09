# Engineering Evidence Engine - Architecture Documentation

## Overview

The Engineering Evidence Engine is the single source of truth for engineering decisions in DevBrain. It transforms raw references from the Reference Intelligence Engine into structured engineering evidence that explains **WHY** those references matter.

### Mission

Reference Intelligence finds references. Evidence Intelligence explains WHY those references matter.

The Evidence Engine becomes the single source of truth for every engineering decision. Nothing should consume raw references anymore.

## Architecture

### Pipeline Integration

```
Question
    ↓
Intent Engine
    ↓
Entity Resolution
    ↓
Reference Intelligence (Finds References)
    ↓
Engineering Evidence Engine (Explains WHY References Matter)
    ↓
Reasoning Engine (Consumes EngineeringEvidence)
    ↓
Simulation Engine (Consumes EngineeringEvidence)
    ↓
Engineering Report (Renders EngineeringEvidence)
```

### Key Principle

**Never consume raw references directly.** Always use `EngineeringEvidence`.

## Data Models

### EngineeringEvidence

The top-level output model containing all structured evidence.

```python
class EngineeringEvidence(BaseModel):
    target_id: UUID
    target_name: str
    target_type: str
    repo_id: UUID
    
    # Evidence Groups
    runtime: Optional[EvidenceGroup]
    configuration: Optional[EvidenceGroup]
    infrastructure: Optional[EvidenceGroup]
    database: Optional[EvidenceGroup]
    testing: Optional[EvidenceGroup]
    public_api: Optional[EvidenceGroup]
    internal_service: Optional[EvidenceGroup]
    external_dependency: Optional[EvidenceGroup]
    
    # Overall Metrics
    total_references: int
    overall_criticality: Criticality
    overall_impact_score: float
    overall_confidence: float
    
    # Executive Summary
    overall_summary: str
    
    # Risk Assessments
    deployment_risk: Optional[RiskAssessment]
    runtime_risk: Optional[RiskAssessment]
    testing_risk: Optional[RiskAssessment]
    configuration_risk: Optional[RiskAssessment]
    database_risk: Optional[RiskAssessment]
    
    # Critical Findings
    critical_findings: List[str]
    
    # Affected Systems
    affected_systems: List[str]
    
    # Recommended Validation Steps
    recommended_validation_steps: List[str]
    
    # Evidence Confidence
    evidence_confidence: float
```

### EvidenceGroup

A group of references with calculated metrics for a specific category.

```python
class EvidenceGroup(BaseModel):
    category: EvidenceCategory
    references: List[Reference]
    
    # Calculated Metrics
    criticality: Criticality
    impact_score: float
    confidence: float
    
    # Engineering Summary
    engineering_summary: str
    highest_risk_references: List[Reference]
    estimated_failure_mode: FailureMode
    risk_drivers: List[str]
    affected_systems: List[str]
    
    # Additional Metrics
    reference_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
```

### Evidence Categories

References are grouped into 8 categories:

1. **RUNTIME** - Function calls, routes, runtime dependencies
2. **CONFIGURATION** - Environment variables, config files
3. **INFRASTRUCTURE** - Docker, Kubernetes, GitHub Actions
4. **DATABASE** - SQL migrations, ORM models, foreign keys
5. **TESTING** - Test files, test dependencies
6. **PUBLIC_API** - API routes, public interfaces
7. **INTERNAL_SERVICE** - Internal service dependencies
8. **EXTERNAL_DEPENDENCY** - External package imports

### Risk Assessment

Risk assessment for each category:

```python
class RiskAssessment(BaseModel):
    category: RiskCategory
    risk_level: Criticality
    risk_score: float
    affected_systems: List[str]
    failure_probability: float
    description: str
```

Risk categories:
- **DEPLOYMENT** - Deployment-related risks
- **RUNTIME** - Runtime-related risks
- **TESTING** - Testing-related risks
- **CONFIGURATION** - Configuration-related risks
- **DATABASE** - Database-related risks

## Core Components

### 1. EngineeringEvidenceEngine

The main orchestrator that transforms references into evidence.

**Responsibilities:**
- Orchestrates grouping and scoring logic
- Creates evidence groups with metrics
- Generates risk assessments
- Produces final `EngineeringEvidence` object

**Key Method:**
```python
def transform_references_to_evidence(
    reference_analysis: ReferenceAnalysisResult
) -> EngineeringEvidence
```

### 2. GroupingLogic

Groups references into evidence categories.

**Responsibilities:**
- Categorizes references by type and location
- Determines failure modes for each category
- Extracts affected systems
- Extracts risk drivers

**Key Method:**
```python
@staticmethod
def group_references(references: List[Reference]) -> dict[EvidenceCategory, List[Reference]]
```

### 3. ScoringLogic

Calculates scores for evidence groups.

**Responsibilities:**
- Calculates criticality levels
- Calculates impact scores
- Calculates confidence scores
- Generates engineering summaries
- Generates risk assessments
- Generates critical findings
- Generates validation steps

**Key Methods:**
```python
@staticmethod
def calculate_criticality(references: List[Reference]) -> Criticality

@staticmethod
def calculate_impact_score(references: List[Reference], category: EvidenceCategory) -> float

@staticmethod
def calculate_confidence(references: List[Reference]) -> float
```

### 4. EngineeringEvidenceService

Pipeline integration service.

**Responsibilities:**
- Orchestrates Reference Intelligence Engine
- Calls Engineering Evidence Engine
- Resolves target IDs and repo paths
- Provides unified interface for the pipeline

**Key Method:**
```python
async def generate_evidence(
    repo_id: UUID,
    target_name: str,
    target_id: Optional[UUID] = None,
    target_type: str = "unknown",
    repo_path: Optional[str] = None,
    db: Optional[AsyncSession] = None
) -> EngineeringEvidence
```

## Scoring Logic

### Criticality Calculation

Criticality is determined by:
1. Presence of CRITICAL references → CRITICAL
2. Presence of HIGH references → HIGH
3. More than 10 references → MEDIUM
4. Otherwise → LOW

### Impact Score Calculation

Impact score formula:
```
base_score = min(reference_count / 50.0, 1.0)
criticality_multiplier = 1.5 if critical_count > 0 else 1.2 if high_count > 0 else 1.0
category_multiplier = category_specific_multiplier (0.7 to 1.3)
impact_score = base_score * criticality_multiplier * category_multiplier
```

Category multipliers:
- RUNTIME: 1.3 (highest impact)
- PUBLIC_API: 1.2
- DATABASE: 1.2
- INFRASTRUCTURE: 1.1
- CONFIGURATION: 1.0
- INTERNAL_SERVICE: 0.9
- TESTING: 0.7
- EXTERNAL_DEPENDENCY: 0.8

### Confidence Calculation

Confidence formula:
```
avg_confidence = average of reference confidences
count_boost = min(reference_count / 20.0, 0.2)
final_confidence = avg_confidence + count_boost
```

### Evidence Confidence

Overall evidence confidence considers:
- Average confidence from all groups
- Coverage boost (more groups = higher confidence)
- Count boost (more references = higher confidence)

## Integration Points

### Reasoning Engine

The Reasoning Engine now consumes `EngineeringEvidence` instead of raw references.

**Changes:**
- Updated `RiskEngine` to use evidence groups for risk assessment
- Updated `DecisionEngine` to use evidence summaries for decisions
- Updated `ReasoningEngine` to extract affected components from evidence groups

**Benefits:**
- More accurate risk assessment based on categorized evidence
- Better decision reasoning with structured summaries
- Clearer affected component identification

### Simulation Engine

The Simulation Engine can optionally consume `EngineeringEvidence` for enhanced simulation.

**Changes:**
- Added optional `evidence` parameter to `simulate_change()`
- Added `_calculate_risk_level_from_evidence()` for evidence-based risk
- Added `_generate_impact_summary_from_evidence()` for evidence-based summaries

**Benefits:**
- More accurate risk assessment using evidence criticality
- Richer impact summaries with evidence group details
- Better cascade failure prediction

### Engineering Report

The Engineering Report now renders `EngineeringEvidence` in the Evidence Section.

**Changes:**
- Updated `EvidenceSection` to accept optional `EngineeringEvidence`
- Added rich evidence data to section content:
  - Evidence groups with metrics
  - Risk assessments by category
  - Critical findings
  - Affected systems
  - Recommended validation steps
- Updated `ReportComposer` to pass evidence to sections
- Updated all section base classes to accept evidence parameter

**Benefits:**
- Richer evidence display in reports
- Structured risk assessment visualization
- Clear validation steps for users
- Better understanding of why references matter

## Example Usage

### DELETE Scenario

**Question:** "Delete AuthService"

**Evidence Output:**
```python
EngineeringEvidence(
    target_name="AuthService",
    total_references=42,
    overall_criticality=Criticality.CRITICAL,
    overall_impact_score=0.87,
    overall_summary="Found 42 total references across 5 dependency categories. Critical dependencies in: runtime, database.",
    
    runtime=EvidenceGroup(
        reference_count=15,
        criticality=Criticality.CRITICAL,
        impact_score=0.92,
        engineering_summary="Found 15 runtime dependencies. Critical dependencies detected. High impact expected. These are runtime dependencies that will cause errors if modified.",
        estimated_failure_mode=FailureMode.RUNTIME_ERROR,
        affected_systems=["UserController", "OrderController", "PaymentController"],
        risk_drivers=["15 critical dependencies that will cause immediate failures", "Runtime dependencies that will cause errors during execution"]
    ),
    
    database=EvidenceGroup(
        reference_count=8,
        criticality=Criticality.CRITICAL,
        impact_score=0.88,
        engineering_summary="Found 8 database dependencies. Critical dependencies detected. High impact expected. These are database dependencies that may require migration planning.",
        estimated_failure_mode=FailureMode.DATA_CORRUPTION,
        affected_systems=["User", "Order", "Payment"],
        risk_drivers=["8 critical references risk data corruption", "Database dependencies that may require migration planning"]
    ),
    
    critical_findings=[
        "CRITICAL: Runtime dependencies contain 5 critical references that will cause system failures",
        "CRITICAL: Database dependencies contain 3 critical references that will cause system failures"
    ],
    
    recommended_validation_steps=[
        "Create comprehensive rollback plan before modification",
        "Implement feature flag for gradual rollout",
        "Prepare hotfix deployment strategy",
        "Plan database migration for schema changes",
        "Backup database before migration"
    ]
)
```

**Report Explanation:**
Instead of simply saying "42 references", the report now explains:
- **Why those references matter:** Critical runtime and database dependencies
- **Which systems are at risk:** UserController, OrderController, PaymentController
- **What will probably fail:** Runtime errors, data corruption
- **Why the decision was reached:** Critical dependencies detected in multiple categories

## Testing

### Unit Tests

Comprehensive unit tests cover:
- Grouping logic for all reference types
- Scoring logic (criticality, impact, confidence)
- Evidence group creation
- Engineering evidence calculation
- Risk assessment generation
- Validation step generation

**Test File:** `tests/test_engineering_evidence_engine.py`

### Integration Tests

Integration tests cover real-world scenarios:
- **DELETE scenarios:** Critical service, unused component, database table
- **RENAME scenarios:** Service with many references, internal function
- **MOVE scenarios:** Module to different package, API route
- **Evidence grouping validation:** Mixed references, confidence validation

**Test File:** `tests/test_engineering_evidence_integration.py`

## Performance Considerations

### Caching

The Engineering Evidence Engine can be integrated with caching strategies:
- Cache evidence by target_id and repo_id
- Invalidate cache when references change
- TTL-based cache expiration

### Parallel Processing

Evidence groups can be processed in parallel:
- Group references in parallel
- Calculate scores for groups in parallel
- Generate risk assessments in parallel

### Batch Processing

For large codebases:
- Process references in batches
- Limit reference counts per group
- Use pagination for large result sets

## Future Enhancements

### Planned Features

1. **Historical Evidence Tracking**
   - Track evidence changes over time
   - Compare evidence snapshots
   - Trend analysis for risk evolution

2. **Evidence Graph Visualization**
   - Visualize dependency graphs
   - Highlight critical paths
   - Interactive exploration

3. **Machine Learning Enhancement**
   - Learn from historical decisions
   - Improve confidence scoring
   - Predict failure modes more accurately

4. **Real-time Evidence Updates**
   - Watch file system changes
   - Update evidence incrementally
   - Push notifications for critical changes

## Migration Guide

### For Existing Code

**Before (consuming raw references):**
```python
references = reference_analysis.references
for ref in references:
    if ref.criticality == Criticality.CRITICAL:
        # Handle critical reference
```

**After (consuming EngineeringEvidence):**
```python
evidence = evidence_engine.transform_references_to_evidence(reference_analysis)
if evidence.runtime and evidence.runtime.criticality == Criticality.CRITICAL:
    # Handle critical runtime dependencies
    for system in evidence.runtime.affected_systems:
        # Handle affected system
```

### For Pipeline Integration

**Before:**
```python
reference_analysis = await reference_engine.analyze_references(...)
decision = reasoning_engine.reason(intent, reference_analysis)
```

**After:**
```python
evidence = await evidence_service.generate_evidence(...)
decision = reasoning_engine.reason(intent, evidence)
```

## Conclusion

The Engineering Evidence Engine transforms DevBrain from a reference-finding tool into an engineering decision support system. By explaining WHY references matter, it enables:

1. **Better Decision Making:** Senior Staff Engineer-level explanations
2. **Risk Awareness:** Clear understanding of potential failures
3. **Actionable Insights:** Specific validation steps and mitigation strategies
4. **Trust:** Transparent evidence-based reasoning

The engine is now the single source of truth for engineering decisions, ensuring consistency across the entire pipeline.
