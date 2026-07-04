from typing import List, Dict, Set, Optional
from uuid import UUID, uuid4
from datetime import datetime
from collections import defaultdict

from app.models.intent import Intent
from app.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    Recommendation,
    DeleteOrderRecommendation,
    RefactorRecommendation,
    TestRecommendation,
    WorkflowRecommendation,
    MigrationRecommendation,
    RollbackStep,
    RollbackPlan,
)
from app.schemas.impact_analysis import (
    AffectedEntity,
    ChangeStep,
    ComplexityScore,
)


class DeleteOrderGenerator:
    """Deterministic delete order recommendations using dependency analysis."""
    
    @staticmethod
    def generate_delete_order(
        affected_entities: List[AffectedEntity],
        change_steps: List[ChangeStep]
    ) -> List[DeleteOrderRecommendation]:
        """
        Generate delete order recommendations based on dependency graph.
        
        Strategy: Delete leaf nodes first (entities with no dependents), then work inward.
        """
        # Build dependency graph: entity_id -> list of entities that depend on it
        dependents_map = defaultdict(list)
        entity_map = {str(e.id): e for e in affected_entities}
        
        # Map change steps to entities
        step_map = {str(s.entity_id): s for s in change_steps}
        
        # Build dependents map from change steps
        for step in change_steps:
            for dep_id in step.dependencies:
                # Convert UUID to string for consistent key handling
                dep_key = str(dep_id) if isinstance(dep_id, UUID) else dep_id
                entity_key = str(step.entity_id) if isinstance(step.entity_id, UUID) else step.entity_id
                dependents_map[dep_key].append(entity_key)
        
        # Calculate deletion order (reverse of dependency order)
        # Entities with no dependents should be deleted first
        deletion_candidates = []
        
        for entity in affected_entities:
            dependents = dependents_map.get(str(entity.id), [])
            
            # Determine if safe to delete
            has_dependents = len(dependents) > 0
            safe_to_delete = not has_dependents
            
            # Determine step number (reverse of change order)
            step = step_map.get(str(entity.id))
            if step:
                # Reverse the order: last to change = first to delete
                delete_step = len(change_steps) - step.step_number + 1
            else:
                delete_step = 0
            
            reason = DeleteOrderGenerator._generate_delete_reason(
                entity, has_dependents, safe_to_delete
            )
            
            rollback_action = DeleteOrderGenerator._generate_rollback_action(entity)
            
            recommendation = DeleteOrderRecommendation(
                step_number=delete_step,
                entity_id=entity.id,
                entity_name=entity.name,
                entity_type=entity.entity_type,
                reason=reason,
                blocking_for=[UUID(d) for d in dependents],
                safe_to_delete=safe_to_delete,
                rollback_action=rollback_action,
            )
            
            deletion_candidates.append(recommendation)
        
        # Sort by step number (ascending)
        deletion_candidates.sort(key=lambda x: x.step_number)
        
        # Assign final step numbers
        for i, rec in enumerate(deletion_candidates, 1):
            rec.step_number = i
        
        return deletion_candidates
    
    @staticmethod
    def _generate_delete_reason(
        entity: AffectedEntity,
        has_dependents: bool,
        safe_to_delete: bool
    ) -> str:
        """Generate reason for deletion recommendation."""
        if not safe_to_delete:
            return f"Has {len(entity.blocking_for) if hasattr(entity, 'blocking_for') else 0} dependents. Delete dependents first."
        
        if entity.impact_level == "critical":
            return f"Critical impact entity. Requires careful coordination and testing."
        
        if entity.impact_level == "high":
            return f"High impact entity. Review dependencies before deletion."
        
        return f"Safe to delete. No direct dependents found."
    
    @staticmethod
    def _generate_rollback_action(entity: AffectedEntity) -> str:
        """Generate rollback action for entity."""
        if entity.entity_type == "service":
            return f"Restore {entity.name} service from backup or redeploy previous version."
        elif entity.entity_type == "model":
            return f"Restore {entity.name} database table from backup or run migration rollback."
        elif entity.entity_type == "api_route":
            return f"Restore {entity.name} API endpoint by reverting code changes."
        elif entity.entity_type == "function":
            return f"Restore {entity.name} function by reverting code changes."
        else:
            return f"Restore {entity.name} by reverting related changes."


class RefactorRecommendationGenerator:
    """Deterministic refactoring recommendations based on complexity analysis."""
    
    @staticmethod
    def generate_refactor_recommendations(
 affected_entities: List[AffectedEntity],
        complexity: ComplexityScore
    ) -> List[RefactorRecommendation]:
        """
        Generate refactoring recommendations based on complexity scores.
        
        Strategy: Recommend refactoring for entities with high complexity.
        """
        recommendations = []
        
        # Thresholds for refactoring
        HIGH_COMPLEXITY_THRESHOLD = 70.0
        MEDIUM_COMPLEXITY_THRESHOLD = 50.0
        
        for entity in affected_entities:
            if entity.impact_level in ["critical", "high"]:
                # High impact entities need refactoring
                current_complexity = complexity.overall_score
                
                if current_complexity > HIGH_COMPLEXITY_THRESHOLD:
                    refactor_type = "extract_method"
                    target_complexity = current_complexity * 0.6  # Reduce by 40%
                    reason = f"High complexity ({current_complexity:.1f}). Extract methods to reduce complexity."
                elif current_complexity > MEDIUM_COMPLEXITY_THRESHOLD:
                    refactor_type = "simplify"
                    target_complexity = current_complexity * 0.8  # Reduce by 20%
                    reason = f"Medium complexity ({current_complexity:.1f}). Simplify logic to improve maintainability."
                else:
                    refactor_type = "rename"
                    target_complexity = current_complexity
                    reason = f"Low complexity but high impact. Consider renaming for clarity."
                
                recommendation = RefactorRecommendation(
                    file_id=None,  # Would be populated from actual file data
                    file_path=f"app/{entity.entity_type}s/{entity.name.lower()}.py",
                    refactor_type=refactor_type,
                    current_complexity=current_complexity,
                    target_complexity=target_complexity,
                    reason=reason,
                    estimated_lines_changed=int(current_complexity * 2),
                )
                
                recommendations.append(recommendation)
        
        # Sort by complexity reduction potential
        recommendations.sort(
            key=lambda x: x.current_complexity - x.target_complexity,
            reverse=True
        )
        
        return recommendations


class TestRecommendationGenerator:
    """Deterministic test recommendations based on impact analysis."""
    
    @staticmethod
    def generate_test_recommendations(
        affected_entities: List[AffectedEntity],
        intent: Intent
    ) -> List[TestRecommendation]:
        """
        Generate test recommendations based on affected entities.
        
        Strategy: Recommend tests for high-impact entities and critical paths.
        """
        recommendations = []
        
        for entity in affected_entities:
            # Determine test type based on entity type
            if entity.entity_type == "service":
                test_type = "integration"
                test_framework = "pytest"
                coverage_target = 0.8
            elif entity.entity_type == "api_route":
                test_type = "integration"
                test_framework = "pytest"
                coverage_target = 0.9
            elif entity.entity_type == "function":
                test_type = "unit"
                test_framework = "pytest"
                coverage_target = 0.95
            elif entity.entity_type == "model":
                test_type = "integration"
                test_framework = "pytest"
                coverage_target = 0.85
            else:
                test_type = "unit"
                test_framework = "pytest"
                coverage_target = 0.8
            
            # Determine priority based on impact level
            priority = entity.impact_level
            
            # Generate reason
            if intent == Intent.DELETE_CODE:
                reason = f"Regression test needed to ensure {entity.name} deletion doesn't break functionality."
            elif intent == Intent.MODIFY_CODE:
                reason = f"Test needed to verify {entity.name} modifications work correctly."
            elif intent == Intent.ADD_FEATURE:
                reason = f"Test needed to verify new {entity.name} functionality."
            else:
                reason = f"Test needed for {entity.name} due to {intent.value} operation."
            
            recommendation = TestRecommendation(
                test_type=test_type,
                target_entity_id=entity.id,
                target_entity_name=entity.name,
                test_framework=test_framework,
                coverage_target=coverage_target,
                priority=priority,
                reason=reason,
            )
            
            recommendations.append(recommendation)
        
        # Sort by priority (critical first)
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda x: priority_order.get(x.priority, 4))
        
        return recommendations


class WorkflowRecommendationGenerator:
    """Deterministic workflow recommendations based on workflow impact."""
    
    @staticmethod
    def generate_workflow_recommendations(
        workflow_names: List[str],
        affected_services: List[str],
        affected_apis: List[str]
    ) -> List[WorkflowRecommendation]:
        """
        Generate workflow review recommendations.
        
        Strategy: Review workflows that include affected services or APIs.
        """
        recommendations = []
        
        for workflow_name in workflow_names:
            # Determine action based on affected components
            has_affected_services = any(s in workflow_name.lower() for s in affected_services)
            has_affected_apis = any(api in workflow_name.lower() for api in affected_apis)
            
            if has_affected_services or has_affected_apis:
                action = "update"
                reason = f"Workflow includes affected services or APIs. Update to reflect changes."
            else:
                action = "review"
                reason = f"Review workflow to ensure no indirect impact from changes."
            
            recommendation = WorkflowRecommendation(
                workflow_id=uuid4(),  # Would be actual workflow ID
                workflow_name=workflow_name,
                action=action,
                reason=reason,
                affected_apis=[api for api in affected_apis if api in workflow_name.lower()],
                affected_services=[svc for svc in affected_services if svc in workflow_name.lower()],
            )
            
            recommendations.append(recommendation)
        
        return recommendations


class MigrationRecommendationGenerator:
    """Deterministic database migration recommendations."""
    
    @staticmethod
    def generate_migration_recommendations(
        affected_databases: List[AffectedEntity],
        intent: Intent
    ) -> List[MigrationRecommendation]:
        """
        Generate database migration recommendations.
        
        Strategy: Generate appropriate migrations based on intent and affected tables.
        """
        recommendations = []
        
        for entity in affected_databases:
            if entity.entity_type != "model":
                continue
            
            if intent == Intent.DELETE_CODE:
                migration_type = "drop_table"
                description = f"Drop table {entity.name} and associated constraints."
                is_destructive = True
                requires_downtime = entity.impact_level in ["critical", "high"]
                rollback_migration = f"CREATE TABLE {entity.name} (/* restore schema */);"
            elif intent == Intent.MODIFY_CODE:
                migration_type = "alter_table"
                description = f"Alter table {entity.name} to reflect schema changes."
                is_destructive = False
                requires_downtime = False
                rollback_migration = f"ALTER TABLE {entity.name} (/* revert changes */);"
            elif intent == Intent.ADD_FEATURE:
                migration_type = "create_table"
                description = f"Create table {entity.name} for new feature."
                is_destructive = False
                requires_downtime = False
                rollback_migration = f"DROP TABLE {entity.name};"
            else:
                migration_type = "alter_table"
                description = f"Modify table {entity.name} for {intent.value} operation."
                is_destructive = False
                requires_downtime = False
                rollback_migration = f"ALTER TABLE {entity.name} (/* revert */);"
            
            recommendation = MigrationRecommendation(
                migration_type=migration_type,
                table_name=entity.name,
                description=description,
                is_destructive=is_destructive,
                requires_downtime=requires_downtime,
                rollback_migration=rollback_migration,
            )
            
            recommendations.append(recommendation)
        
        return recommendations


class RollbackPlanGenerator:
    """Deterministic rollback plan generation."""
    
    @staticmethod
    def generate_rollback_plan(
        change_steps: List[ChangeStep],
        affected_databases: List[AffectedEntity]
    ) -> RollbackPlan:
        """
        Generate a rollback plan based on change steps.
        
        Strategy: Reverse the change order for rollback.
        """
        # Reverse change steps for rollback
        rollback_steps = []
        
        for i, step in enumerate(reversed(change_steps), 1):
            rollback_step = RollbackStep(
                step_number=i,
                action="revert",
                target=step.entity_name,
                command=f"Revert changes to {step.entity_name} ({step.entity_type})",
                estimated_time_seconds=int(step.estimated_effort_hours * 3600),
                verification=f"Verify {step.entity_name} is restored to previous state",
            )
            rollback_steps.append(rollback_step)
        
        # Add database rollback steps if needed
        for db_entity in affected_databases:
            if db_entity.entity_type == "model":
                step = RollbackStep(
                    step_number=len(rollback_steps) + 1,
                    action="restore",
                    target=db_entity.name,
                    command=f"Run database migration rollback for {db_entity.name}",
                    estimated_time_seconds=300,  # 5 minutes
                    verification=f"Verify {db_entity.name} table structure is restored",
                )
                rollback_steps.append(step)
        
        total_time = sum(s.estimated_time_seconds for s in rollback_steps)
        
        # Determine if rollback can be automated
        # Based on impact level: high/critical impact requires manual intervention
        can_automate = all(
            db.impact_level not in ["critical", "high"]
            for db in affected_databases 
            if db.entity_type == "model"
        )
        
        # Determine data loss risk
        has_destructive_changes = any(
            db.impact_level in ["critical", "high"]
            for db in affected_databases
            if db.entity_type == "model"
        )
        
        data_loss_risk = "high" if has_destructive_changes else "low"
        
        return RollbackPlan(
            plan_id=str(uuid4()),
            total_steps=len(rollback_steps),
            total_estimated_time_seconds=total_time,
            steps=rollback_steps,
            can_rollback_automatically=can_automate,
            manual_intervention_required=not can_automate,
            data_loss_risk=data_loss_risk,
        )


class RecommendationEngine:
    """
    Main Recommendation Engine service.
    
    This deterministic engine generates deterministic engineering recommendations
    using rule-based algorithms and dependency analysis. No LLM is used.
    Designed to support future Root Cause Intelligence.
    """
    
    def __init__(self):
        self.delete_order_generator = DeleteOrderGenerator()
        self.refactor_generator = RefactorRecommendationGenerator()
        self.test_generator = TestRecommendationGenerator()
        self.workflow_generator = WorkflowRecommendationGenerator()
        self.migration_generator = MigrationRecommendationGenerator()
        self.rollback_generator = RollbackPlanGenerator()
    
    def generate_recommendations(
        self,
        request: RecommendationRequest
    ) -> RecommendationResponse:
        """
        Generate engineering recommendations based on intent, evidence, and impact.
        
        Args:
            request: Recommendation request with intent, evidence, and impact
            
        Returns:
            RecommendationResponse with structured recommendations
        """
        recommendations = []
        
        # Extract data from evidence and impact
        affected_entities = []
        change_steps = []
        complexity = None
        workflow_names = []
        
        if request.impact:
            affected_entities = (
                request.impact.affected_services +
                request.impact.affected_databases +
                request.impact.breaking_apis
            )
            change_steps = request.impact.recommended_change_order
            complexity = request.impact.engineering_complexity
            workflow_names = [w.name for w in request.impact.affected_workflows]
        
        # Generate delete order recommendations for DELETE_CODE intent
        if request.intent == Intent.DELETE_CODE and change_steps:
            delete_order = self.delete_order_generator.generate_delete_order(
                affected_entities, change_steps
            )
            recommendations.extend([
                Recommendation(
                    id=str(uuid4()),
                    type="delete_order",
                    priority="critical",
                    title=f"Delete {rec.entity_name}",
                    description=rec.reason,
                    entity_id=rec.entity_id,
                    entity_name=rec.entity_name,
                    entity_type=rec.entity_type,
                    action="delete",
                    estimated_effort_hours=1.0,
                    dependencies=[],
                    risk_level="high" if not rec.safe_to_delete else "medium",
                    confidence=0.9,
                )
                for rec in delete_order
            ])
        
        # Generate refactor recommendations
        if complexity:
            refactor_recs = self.refactor_generator.generate_refactor_recommendations(
                affected_entities, complexity
            )
            recommendations.extend([
                Recommendation(
                    id=str(uuid4()),
                    type="refactor",
                    priority="high" if rec.current_complexity > 70 else "medium",
                    title=f"Refactor {rec.file_path}",
                    description=rec.reason,
                    entity_id=rec.file_id,
                    entity_name=rec.file_path,
                    entity_type="file",
                    action=rec.refactor_type,
                    estimated_effort_hours=rec.estimated_lines_changed / 50.0,
                    dependencies=[],
                    risk_level="medium",
                    confidence=0.85,
                )
                for rec in refactor_recs
            ])
        
        # Generate test recommendations
        test_recs = []
        if request.include_tests and affected_entities:
            test_recs = self.test_generator.generate_test_recommendations(
                affected_entities, request.intent
            )
            recommendations.extend([
                Recommendation(
                    id=str(uuid4()),
                    type="test",
                    priority=rec.priority,
                    title=f"Test {rec.target_entity_name}",
                    description=rec.reason,
                    entity_id=rec.target_entity_id,
                    entity_name=rec.target_entity_name,
                    entity_type="test",
                    action=f"write_{rec.test_type}_test",
                    estimated_effort_hours=2.0 if rec.priority == "critical" else 1.0,
                    dependencies=[],
                    risk_level="low",
                    confidence=0.9,
                )
                for rec in test_recs
            ])
        
        # Generate workflow recommendations
        workflow_recs = []
        if workflow_names:
            workflow_recs = self.workflow_generator.generate_workflow_recommendations(
                workflow_names,
                [e.name for e in affected_entities if e.entity_type == "service"],
                [e.name for e in affected_entities if e.entity_type == "api_route"]
            )
            recommendations.extend([
                Recommendation(
                    id=str(uuid4()),
                    type="workflow",
                    priority="medium",
                    title=f"{rec.action.capitalize()} {rec.workflow_name}",
                    description=rec.reason,
                    entity_id=rec.workflow_id,
                    entity_name=rec.workflow_name,
                    entity_type="workflow",
                    action=rec.action,
                    estimated_effort_hours=1.0,
                    dependencies=[],
                    risk_level="low",
                    confidence=0.8,
                )
                for rec in workflow_recs
            ])
        
        # Generate migration recommendations
        migration_recs = []
        if affected_entities:
            migration_recs = self.migration_generator.generate_migration_recommendations(
                affected_entities, request.intent
            )
        recommendations.extend([
            Recommendation(
                id=str(uuid4()),
                type="migration",
                priority="critical" if rec.is_destructive else "high",
                title=f"{rec.migration_type} {rec.table_name}",
                description=rec.description,
                entity_id=None,
                entity_name=rec.table_name,
                entity_type="database",
                action=rec.migration_type,
                estimated_effort_hours=4.0 if rec.requires_downtime else 2.0,
                dependencies=[],
                risk_level="high" if rec.is_destructive else "medium",
                confidence=0.9,
            )
            for rec in migration_recs
        ])
        
        # Generate rollback plan if requested
        rollback_plan = None
        if request.include_rollback and change_steps:
            rollback_plan = self.rollback_generator.generate_rollback_plan(
                change_steps,
                [e for e in affected_entities if e.entity_type == "model"]
            )
        
        # Count priorities
        critical_count = sum(1 for r in recommendations if r.priority == "critical")
        high_count = sum(1 for r in recommendations if r.priority == "high")
        
        # Calculate total effort
        total_effort = sum(r.estimated_effort_hours for r in recommendations)
        
        return RecommendationResponse(
            intent=request.intent,
            target=request.target,
            recommendations=recommendations,
            delete_order=delete_order if request.intent == Intent.DELETE_CODE else [],
            refactor_recommendations=refactor_recs if complexity else [],
            test_recommendations=test_recs if request.include_tests else [],
            workflow_recommendations=workflow_recs if workflow_names else [],
            migration_recommendations=migration_recs,
            rollback_plan=rollback_plan,
            total_recommendations=len(recommendations),
            critical_count=critical_count,
            high_count=high_count,
            total_estimated_effort_hours=round(total_effort, 2),
            generation_method="deterministic",
            confidence=0.85,
            analysis_timestamp=datetime.utcnow().isoformat(),
        )
