# Evidence Intelligence Engine - Integration Plan

**Version:** 1.0  
**Date:** July 5, 2026  
**Status:** Integration Plan  
**Authors:** Chief Software Architect  

---

## Executive Summary

The Evidence Intelligence Engine transforms raw references from the Reference Intelligence Engine into structured engineering evidence. This document outlines the integration plan for consuming EngineeringEvidence in the Reasoning Engine, Simulation Engine, and Engineering Report.

**Goal:** Replace raw reference consumption with structured evidence consumption across all engineering decision components.

---

## Architecture Overview

### Current Architecture

```
User Query
    ↓
Entity Resolution
    ↓
Reference Intelligence Engine
    ↓
Raw References (ReferenceAnalysisResult)
    ↓
┌─────────────┬──────────────┬──────────────┐
│ Reasoning   │ Simulation   │ Engineering  │
│ Engine      │ Engine       │ Report       │
└─────────────┴──────────────┴──────────────┘
```

### Target Architecture

```
User Query
    ↓
Entity Resolution
    ↓
Reference Intelligence Engine
    ↓
Raw References (ReferenceAnalysisResult)
    ↓
Evidence Intelligence Engine
    ↓
Structured Evidence (EngineeringEvidence)
    ↓
┌─────────────┬──────────────┬──────────────┐
│ Reasoning   │ Simulation   │ Engineering  │
│ Engine      │ Engine       │ Report       │
└─────────────┴──────────────┴──────────────┘
```

---

## Integration Points

### 1. Reasoning Engine Integration

**Current State:**
- Consumes raw references from ReferenceAnalysisResult
- Manually calculates criticality and impact
- Generates reasoning based on raw reference lists

**Target State:**
- Consumes EngineeringEvidence from Evidence Intelligence Engine
- Uses pre-calculated criticality, impact, confidence
- Generates reasoning based on structured evidence groups

**Integration Steps:**

1. **Update Reasoning Engine Input**
   ```python
   # Current
   async def generate_reasoning(
       self,
       reference_analysis: ReferenceAnalysisResult,
       ...
   ) -> dict:
       # Manual processing of raw references
   
   # Target
   async def generate_reasoning(
       self,
       evidence: EngineeringEvidence,
       ...
   ) -> dict:
       # Use structured evidence groups
   ```

2. **Update Reasoning Logic**
   - Use `evidence.runtime_dependencies` for runtime impact analysis
   - Use `evidence.database_dependencies` for database impact analysis
   - Use `evidence.overall_criticality` for risk assessment
   - Use `evidence.estimated_failure_modes` for failure prediction
   - Use `evidence.recommended_actions` for recommendations

3. **Update Reasoning Output**
   - Include evidence group summaries in reasoning
   - Reference specific evidence groups in explanations
   - Use failure modes from evidence

**Files to Modify:**
- `backend/app/services/reasoning_engine.py`

**Estimated Effort:** 2-3 hours

---

### 2. Simulation Engine Integration

**Current State:**
- Consumes raw references from graph traversal
- Manually calculates cascade effects
- Generates timeline based on raw node lists

**Target State:**
- Consumes EngineeringEvidence from Evidence Intelligence Engine
- Uses evidence groups for cascade prediction
- Generates timeline based on structured evidence

**Integration Steps:**

1. **Update Simulation Engine Input**
   ```python
   # Current
   async def simulate_change(
       self,
       db: AsyncSession,
       target_node: RepositoryNode,
       change_type: str,
       ...
   ) -> dict:
       # Manual graph traversal
   
   # Target
   async def simulate_change(
       self,
       db: AsyncSession,
       target_node: RepositoryNode,
       evidence: EngineeringEvidence,
       change_type: str,
       ...
   ) -> dict:
       # Use structured evidence for simulation
   ```

2. **Update Simulation Logic**
   - Use `evidence.runtime_dependencies` for runtime cascade prediction
   - Use `evidence.database_dependencies` for database cascade prediction
   - Use `evidence.estimated_failure_modes` for failure mode prediction
   - Use `evidence.highest_risk_references` for critical path identification

3. **Update Simulation Output**
   - Include evidence group impact in simulation results
   - Reference specific failure modes in timeline
   - Use evidence confidence for simulation confidence

**Files to Modify:**
- `backend/app/services/simulation_engine.py`

**Estimated Effort:** 3-4 hours

---

### 3. Engineering Report Integration

**Current State:**
- Consumes raw references from various sources
- Manually formats reference lists
- Generates report sections from raw data

**Target State:**
- Consumes EngineeringEvidence from Evidence Intelligence Engine
- Displays structured evidence groups
- Generates report sections from evidence

**Integration Steps:**

1. **Update Report Generation**
   ```python
   # Current
   def generate_report(
       self,
       reference_analysis: ReferenceAnalysisResult,
       reasoning: dict,
       simulation: dict,
       ...
   ) -> EngineeringReport:
       # Manual formatting of raw references
   
   # Target
   def generate_report(
       self,
       evidence: EngineeringEvidence,
       reasoning: dict,
       simulation: dict,
       ...
   ) -> EngineeringReport:
       # Use structured evidence for report
   ```

2. **Update Report Sections**
   - **Executive Summary:** Use `evidence.executive_summary`
   - **Risk Assessment:** Use `evidence.risk_assessment`
   - **Runtime Dependencies:** Display `evidence.runtime_dependencies`
   - **Configuration Dependencies:** Display `evidence.configuration_dependencies`
   - **Database Dependencies:** Display `evidence.database_dependencies`
   - **Infrastructure Dependencies:** Display `evidence.infrastructure_dependencies`
   - **Testing Dependencies:** Display `evidence.testing_dependencies`
   - **Recommended Actions:** Use `evidence.recommended_actions`

3. **Update Report Display**
   - Show evidence group metrics (criticality, impact, confidence)
   - Display highest risk references per group
   - Show estimated failure modes
   - Include engineering summaries

**Files to Modify:**
- `backend/app/services/report_generator.py`
- Frontend components (if displaying evidence directly)

**Estimated Effort:** 4-5 hours

---

## Integration Workflow

### Complete Pipeline

```python
# 1. Entity Resolution
entity_extraction = entity_extractor.extract(query)
node_resolution = await node_resolver.resolve(db, repo_id, entity_extraction.target_name)

# 2. Reference Intelligence Engine
reference_engine = ReferenceIntelligenceEngine()
reference_analysis = await reference_engine.analyze_references(
    repo_id=repo_id,
    repo_path=repo_path,
    target_name=node_resolution.node.name,
    target_id=node_resolution.node.id,
    target_type=node_resolution.node.node_type.value
)

# 3. Evidence Intelligence Engine
evidence_engine = EvidenceIntelligenceEngine()
evidence = evidence_engine.transform_references_to_evidence(reference_analysis)

# 4. Reasoning Engine (consumes evidence)
reasoning = await reasoning_engine.generate_reasoning(
    evidence=evidence,
    change_type=entity_extraction.action,
    ...
)

# 5. Simulation Engine (consumes evidence)
simulation = await simulation_engine.simulate_change(
    db=db,
    target_node=node_resolution.node,
    evidence=evidence,
    change_type=entity_extraction.action,
    ...
)

# 6. Engineering Report (consumes evidence)
report = report_generator.generate_report(
    evidence=evidence,
    reasoning=reasoning,
    simulation=simulation,
    ...
)
```

---

## Migration Strategy

### Phase 1: Evidence Engine Integration (Week 1)

**Goal:** Integrate Evidence Intelligence Engine into the pipeline

**Steps:**
1. Add Evidence Intelligence Engine to service layer
2. Update API endpoint to call Evidence Engine after Reference Engine
3. Verify evidence generation works correctly
4. Add logging for evidence transformation

**Success Criteria:**
- Evidence Engine successfully transforms references to evidence
- Evidence groups are correctly populated
- Metrics are calculated accurately

---

### Phase 2: Reasoning Engine Migration (Week 2)

**Goal:** Update Reasoning Engine to consume EngineeringEvidence

**Steps:**
1. Update Reasoning Engine input signature
2. Update reasoning logic to use evidence groups
3. Update reasoning output to reference evidence
4. Add unit tests for evidence-based reasoning
5. Integration test with full pipeline

**Success Criteria:**
- Reasoning Engine consumes EngineeringEvidence
- Reasoning quality maintained or improved
- Unit tests pass
- Integration tests pass

---

### Phase 3: Simulation Engine Migration (Week 3)

**Goal:** Update Simulation Engine to consume EngineeringEvidence

**Steps:**
1. Update Simulation Engine input signature
2. Update simulation logic to use evidence groups
3. Update simulation output to reference evidence
4. Add unit tests for evidence-based simulation
5. Integration test with full pipeline

**Success Criteria:**
- Simulation Engine consumes EngineeringEvidence
- Simulation accuracy maintained or improved
- Unit tests pass
- Integration tests pass

---

### Phase 4: Engineering Report Migration (Week 4)

**Goal:** Update Engineering Report to consume EngineeringEvidence

**Steps:**
1. Update Report Generator input signature
2. Update report sections to display evidence groups
3. Update report display logic
4. Add unit tests for evidence-based reports
5. Integration test with full pipeline

**Success Criteria:**
- Report Generator consumes EngineeringEvidence
- Report quality maintained or improved
- Unit tests pass
- Integration tests pass

---

### Phase 5: Validation and Rollout (Week 5)

**Goal:** Validate complete pipeline and deploy to production

**Steps:**
1. End-to-end integration testing
2. Performance testing
3. User acceptance testing
4. Documentation updates
5. Production deployment

**Success Criteria:**
- All integration tests pass
- Performance within acceptable limits
- User acceptance criteria met
- Documentation updated
- Production deployment successful

---

## Backward Compatibility

### Transition Period

During migration, maintain backward compatibility:

```python
async def generate_reasoning(
    self,
    reference_analysis: Optional[ReferenceAnalysisResult] = None,
    evidence: Optional[EngineeringEvidence] = None,
    ...
) -> dict:
    """Generate reasoning with backward compatibility."""
    
    # If evidence provided, use it
    if evidence:
        return self._generate_reasoning_from_evidence(evidence, ...)
    
    # If reference_analysis provided, transform to evidence (legacy)
    if reference_analysis:
        evidence_engine = EvidenceIntelligenceEngine()
        evidence = evidence_engine.transform_references_to_evidence(reference_analysis)
        return self._generate_reasoning_from_evidence(evidence, ...)
    
    # Fallback to legacy method
    return self._generate_reasoning_legacy(...)
```

### Deprecation Timeline

- **Week 1-4:** Support both ReferenceAnalysisResult and EngineeringEvidence
- **Week 5:** Deprecate ReferenceAnalysisResult support
- **Week 6:** Remove legacy code

---

## Testing Strategy

### Unit Tests

**Evidence Engine:**
- Test grouping logic for all reference types
- Test scoring logic for all metrics
- Test evidence transformation
- Test edge cases (empty references, single reference, etc.)

**Reasoning Engine:**
- Test reasoning with evidence input
- Test reasoning quality with evidence vs raw references
- Test all evidence group consumption

**Simulation Engine:**
- Test simulation with evidence input
- Test simulation accuracy with evidence vs raw references
- Test failure mode prediction

**Report Generator:**
- Test report generation with evidence input
- Test report quality with evidence vs raw references
- Test all evidence group display

### Integration Tests

**Full Pipeline:**
- Test complete pipeline from query to report
- Test all operation types (DELETE, RENAME, MOVE, EXTRACT)
- Test edge cases (no references, many references, etc.)

### Performance Tests

**Evidence Engine:**
- Test transformation time for 100, 1000, 10000 references
- Test memory usage for large reference sets

**Full Pipeline:**
- Test end-to-end time with evidence engine
- Compare performance to baseline

---

## Risk Mitigation

### Risk 1: Evidence Quality Degradation

**Mitigation:**
- Comprehensive unit tests for grouping and scoring logic
- A/B testing with legacy reasoning/simulation
- Manual review of evidence for critical scenarios

### Risk 2: Performance Regression

**Mitigation:**
- Performance testing before deployment
- Optimization of evidence transformation if needed
- Caching of evidence for repeated queries

### Risk 3: Integration Complexity

**Mitigation:**
- Phased migration approach
- Backward compatibility during transition
- Comprehensive integration testing

### Risk 4: Breaking Changes

**Mitigation:**
- Maintain backward compatibility during transition
- Clear deprecation timeline
- Communication with stakeholders

---

## Success Metrics

### Quality Metrics

- **Evidence Accuracy:** >95% correct grouping
- **Scoring Accuracy:** >90% accurate criticality/impact/confidence
- **Reasoning Quality:** Maintained or improved vs baseline
- **Simulation Accuracy:** Maintained or improved vs baseline
- **Report Quality:** Maintained or improved vs baseline

### Performance Metrics

- **Evidence Transformation:** <100ms for 1000 references
- **Full Pipeline:** <2x baseline time
- **Memory Usage:** <1.5x baseline memory

### Adoption Metrics

- **Integration Coverage:** 100% of consumers migrated
- **Test Coverage:** >90% for new code
- **Documentation:** 100% of APIs documented

---

## Rollback Plan

If critical issues are discovered:

1. **Immediate Rollback:** Revert to legacy ReferenceAnalysisResult consumption
2. **Hotfix:** Fix identified issues in Evidence Engine
3. **Re-deploy:** Re-deploy with fixes
4. **Validation:** Re-run integration tests
5. **Resume Migration:** Continue migration after validation

---

## Conclusion

The Evidence Intelligence Engine provides a structured, reusable layer for engineering evidence. Integration with Reasoning Engine, Simulation Engine, and Engineering Report will improve consistency, reduce duplication, and enable better engineering decisions.

**Timeline:** 5 weeks  
**Effort:** 15-20 hours  
**Risk:** Medium (mitigated by phased migration and backward compatibility)  
**Impact:** High (improves quality, consistency, and maintainability)
