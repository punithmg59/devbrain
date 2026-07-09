"""
Engineering Intelligence Service

Generates comprehensive, repository-aware engineering intelligence responses.
Provides engineering decisions, evidence, analysis, and actionable recommendations.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from collections import OrderedDict

from ..utils.logging_config import get_logger
from ..utils.graph_utils import ensure_deterministic_order

from ..schemas.engineering_intelligence import (
    EngineeringIntelligenceResponse,
    EngineeringDecision,
    EngineeringEvidence,
    RepositoryAnalysis,
    AffectedComponent,
    RiskAssessment,
    RecommendedChange,
    ImplementationStep,
    ImplementationPlan,
    TestItem,
    TestingChecklist,
    EngineeringAction
)
from .engineering_evidence.models import EngineeringEvidence as RepoEvidence
from .intent.schemas import IntentType

logger = get_logger(__name__)


class EngineeringIntelligenceService:
    """
    Engineering Intelligence Service for comprehensive engineering analysis.
    
    This service generates repository-aware engineering intelligence including:
    - Engineering decisions with rationale
    - Repository evidence and analysis
    - Affected components identification
    - Risk assessment
    - Recommended changes
    - Implementation plans
    - Testing checklists
    - Actionable engineering steps
    """
    
    def __init__(self):
        """Initialize the Engineering Intelligence Service."""
        logger.info("Engineering Intelligence Service initialized")
    
    def generate_intelligence_response(
        self,
        question: str,
        intent: IntentType,
        target_name: str,
        repo_evidence: RepoEvidence,
        engine_result: Dict[str, Any]
    ) -> EngineeringIntelligenceResponse:
        """
        Generate a comprehensive engineering intelligence response.
        
        Args:
            question: The original engineering question
            intent: The classified intent
            target_name: The target entity name
            repo_evidence: Repository evidence from EngineeringEvidenceEngine
            engine_result: Result from the specific backend engine
            
        Returns:
            Comprehensive EngineeringIntelligenceResponse
        """
        logger.info(f"Generating engineering intelligence for intent={intent}, target={target_name}")
        
        # Generate engineering decision
        engineering_decision = self._generate_engineering_decision(
            intent, target_name, repo_evidence, engine_result
        )
        
        # Generate engineering evidence
        engineering_evidence = self._generate_engineering_evidence(repo_evidence)
        
        # Generate repository analysis
        repository_analysis = self._generate_repository_analysis(repo_evidence)
        
        # Identify affected components
        affected_components = self._identify_affected_components(
            intent, target_name, repo_evidence, engine_result
        )
        
        # Generate risk assessment
        risk_assessment = self._generate_risk_assessment(
            intent, target_name, repo_evidence, affected_components
        )
        
        # Generate recommended changes
        recommended_changes = self._generate_recommended_changes(
            intent, target_name, repo_evidence, engine_result
        )
        
        # Generate implementation plan
        implementation_plan = self._generate_implementation_plan(
            intent, target_name, repo_evidence, recommended_changes
        )
        
        # Generate testing checklist
        testing_checklist = self._generate_testing_checklist(
            intent, target_name, repo_evidence, implementation_plan
        )
        
        # Generate engineering actions
        engineering_actions = self._generate_engineering_actions(
            intent, target_name, recommended_changes, implementation_plan
        )
        
        # Build response
        response = EngineeringIntelligenceResponse(
            question=question,
            intent=intent.value if hasattr(intent, 'value') else str(intent),
            target_name=target_name,
            engineering_decision=engineering_decision,
            engineering_evidence=engineering_evidence,
            repository_analysis=repository_analysis,
            affected_components=affected_components,
            risk_assessment=risk_assessment,
            recommended_changes=recommended_changes,
            implementation_plan=implementation_plan,
            testing_checklist=testing_checklist,
            engineering_actions=engineering_actions,
            grounded_in_repository=repo_evidence.evidence_confidence > 0.5,
            evidence_confidence=repo_evidence.evidence_confidence,
            processing_time_ms=engine_result.get("processing_time_ms", 0),
            limitations=repo_evidence.limitations
        )
        
        logger.info(f"Engineering intelligence generated: confidence={repo_evidence.evidence_confidence:.2f}")
        return response
    
    def _generate_engineering_decision(
        self,
        intent: IntentType,
        target_name: str,
        repo_evidence: RepoEvidence,
        engine_result: Dict[str, Any]
    ) -> EngineeringDecision:
        """Generate the primary engineering decision."""
        
        # Base decision on intent and repository evidence
        decision_map = {
            IntentType.DELETE: f"Proceed with deletion of {target_name} with caution",
            IntentType.RENAME: f"Rename {target_name} to the suggested name",
            IntentType.MOVE: f"Move {target_name} to the recommended location",
            IntentType.MODIFY: f"Modify {target_name} according to requirements",
            IntentType.REFACTOR: f"Refactor {target_name} to improve code quality",
            IntentType.ADD_FEATURE: f"Implement the new feature as specified",
            IntentType.DEPENDENCY: f"Address the identified dependencies",
            IntentType.DEPENDENCY_QUERY: f"Analyze and document dependencies",
            IntentType.REPOSITORY_QUERY: f"Explore repository structure",
            IntentType.ARCHITECTURE: f"Analyze and document architecture",
            IntentType.ARCHITECTURE_GUIDANCE: f"Follow architectural guidance",
            IntentType.FEATURE_PLANNING: f"Implement feature according to plan",
            IntentType.REFACTORING_GUIDANCE: f"Apply refactoring recommendations",
            IntentType.EXPLAIN: f"Document and explain the component"
        }
        
        decision = decision_map.get(intent, f"Analyze {target_name}")
        
        # Build rationale based on repository evidence
        rationale_parts = [
            f"Based on repository analysis of {target_name}",
            f"Found {len(repo_evidence.ast_nodes)} AST nodes",
            f"Identified {len(repo_evidence.classes)} classes",
            f"Found {len(repo_evidence.functions)} functions",
        ]
        
        if repo_evidence.dependency_graph:
            rationale_parts.append(f"Dependency graph has {repo_evidence.dependency_graph.total_edges} edges")
        
        rationale = ". ".join(rationale_parts) + "."
        
        # Calculate confidence based on evidence
        confidence = repo_evidence.evidence_confidence
        
        # Generate alternatives based on intent
        alternatives = []
        if intent in [IntentType.DELETE, IntentType.MODIFY, IntentType.REFACTOR]:
            alternatives.append(f"Consider deprecation instead of {intent.value.lower()}")
            alternatives.append(f"Implement feature flags for gradual rollout")
        elif intent == IntentType.ADD_FEATURE:
            alternatives.append(f"Consider implementing as a separate service")
            alternatives.append(f"Evaluate existing solutions before building custom")
        
        return EngineeringDecision(
            decision=decision,
            rationale=rationale,
            confidence=confidence,
            alternatives=alternatives
        )
    
    def _generate_engineering_evidence(self, repo_evidence: RepoEvidence) -> EngineeringEvidence:
        """Generate engineering evidence summary."""
        
        data_sources = []
        if repo_evidence.ast_nodes:
            data_sources.append("AST analysis")
        if repo_evidence.dependency_graph:
            data_sources.append("Dependency graph")
        if repo_evidence.call_graph:
            data_sources.append("Call graph")
        if repo_evidence.classes:
            data_sources.append("Class definitions")
        if repo_evidence.functions:
            data_sources.append("Function signatures")
        if repo_evidence.api_routes:
            data_sources.append("API routes")
        if repo_evidence.imports:
            data_sources.append("Import analysis")
        
        key_findings = []
        if repo_evidence.total_references > 0:
            key_findings.append(f"Found {repo_evidence.total_references} references")
        if len(repo_evidence.classes) > 0:
            key_findings.append(f"Identified {len(repo_evidence.classes)} classes")
        if len(repo_evidence.functions) > 0:
            key_findings.append(f"Identified {len(repo_evidence.functions)} functions")
        if repo_evidence.dependency_graph and repo_evidence.dependency_graph.total_edges > 0:
            key_findings.append(f"Found {repo_evidence.dependency_graph.total_edges} dependencies")
        
        evidence_summary = f"Repository evidence collected from {len(data_sources)} data sources. "
        evidence_summary += f"Overall evidence confidence: {repo_evidence.evidence_confidence:.2f}."
        
        return EngineeringEvidence(
            evidence_summary=evidence_summary,
            data_sources=data_sources,
            evidence_confidence=repo_evidence.evidence_confidence,
            key_findings=key_findings
        )
    
    def _generate_repository_analysis(self, repo_evidence: RepoEvidence) -> RepositoryAnalysis:
        """Generate repository structure analysis."""
        
        # Build structure summary
        structure_parts = []
        if repo_evidence.classes:
            structure_parts.append(f"Contains {len(repo_evidence.classes)} classes")
        if repo_evidence.functions:
            structure_parts.append(f"Contains {len(repo_evidence.functions)} functions")
        if repo_evidence.api_routes:
            structure_parts.append(f"Exposes {len(repo_evidence.api_routes)} API routes")
        if repo_evidence.imports:
            structure_parts.append(f"Uses {len(repo_evidence.imports)} imports")
        
        structure_summary = ". ".join(structure_parts) if structure_parts else "Limited structure information available"
        
        # Identify patterns
        patterns = []
        if any(cls.name.endswith("Service") for cls in repo_evidence.classes):
            patterns.append("Service layer pattern detected")
        if any(cls.name.endswith("Controller") for cls in repo_evidence.classes):
            patterns.append("Controller pattern detected")
        if any(cls.name.endswith("Repository") for cls in repo_evidence.classes):
            patterns.append("Repository pattern detected")
        
        # Code metrics
        code_metrics = {
            "total_classes": len(repo_evidence.classes),
            "total_functions": len(repo_evidence.functions),
            "total_api_routes": len(repo_evidence.api_routes),
            "total_imports": len(repo_evidence.imports),
            "ast_nodes_count": len(repo_evidence.ast_nodes)
        }
        
        # Key dependencies
        dependencies = []
        for imp in repo_evidence.imports[:10]:  # Top 10 imports
            dependencies.append(imp.module)
        
        return RepositoryAnalysis(
            structure_summary=structure_summary,
            patterns_identified=patterns,
            code_metrics=code_metrics,
            dependencies=dependencies
        )
    
    def _identify_affected_components(
        self,
        intent: IntentType,
        target_name: str,
        repo_evidence: RepoEvidence,
        engine_result: Dict[str, Any]
    ) -> List[AffectedComponent]:
        """Identify components affected by the engineering change."""
        
        affected = []
        
        # Add classes that might be affected (sorted for determinism)
        sorted_classes = sorted(repo_evidence.classes, key=lambda x: x.name)
        for cls in sorted_classes:
            impact_level = "medium"
            impact_description = f"Class {cls.name} may be affected by changes to {target_name}"
            
            if target_name.lower() in cls.name.lower():
                impact_level = "high"
                impact_description = f"Class {cls.name} is directly related to {target_name}"
            
            affected.append(AffectedComponent(
                name=cls.name,
                type="class",
                file_path=cls.file_path,
                impact_level=impact_level,
                impact_description=impact_description,
                required_changes=["Review class implementation", "Update references if needed"]
            ))
        
        # Add functions that might be affected (sorted for determinism)
        sorted_functions = sorted(repo_evidence.functions[:20], key=lambda x: x.name)
        for func in sorted_functions:
            impact_level = "low"
            impact_description = f"Function {func.name} may be affected"
            
            if target_name.lower() in func.name.lower():
                impact_level = "medium"
                impact_description = f"Function {func.name} is related to {target_name}"
            
            affected.append(AffectedComponent(
                name=func.name,
                type="function",
                file_path=func.file_path,
                impact_level=impact_level,
                impact_description=impact_description,
                required_changes=["Review function implementation"]
            ))
        
        # Add API routes that might be affected (sorted for determinism)
        sorted_routes = sorted(repo_evidence.api_routes, key=lambda x: x.path)
        for route in sorted_routes:
            if target_name.lower() in route.path.lower():
                affected.append(AffectedComponent(
                    name=route.path,
                    type="api_route",
                    file_path=route.file_path,
                    impact_level="high",
                    impact_description=f"API route {route.path} directly references {target_name}",
                    required_changes=["Update route handler", "Test endpoint"]
                ))
        
        # Sort affected components by name for determinism
        affected = sorted(affected, key=lambda x: x.name)
        
        return affected
    
    def _generate_risk_assessment(
        self,
        intent: IntentType,
        target_name: str,
        repo_evidence: RepoEvidence,
        affected_components: List[AffectedComponent]
    ) -> RiskAssessment:
        """Generate risk assessment for the engineering change."""
        
        # Calculate overall risk based on affected components
        critical_count = sum(1 for c in affected_components if c.impact_level == "critical")
        high_count = sum(1 for c in affected_components if c.impact_level == "high")
        
        if critical_count > 0:
            overall_risk = "critical"
            probability_of_failure = 0.7
        elif high_count > 3:
            overall_risk = "high"
            probability_of_failure = 0.5
        elif high_count > 0:
            overall_risk = "medium"
            probability_of_failure = 0.3
        else:
            overall_risk = "low"
            probability_of_failure = 0.1
        
        # Risk factors
        risk_factors = []
        if len(affected_components) > 10:
            risk_factors.append(f"High number of affected components ({len(affected_components)})")
        if repo_evidence.evidence_confidence < 0.5:
            risk_factors.append("Low evidence confidence may hide dependencies")
        if intent in [IntentType.DELETE, IntentType.MODIFY]:
            risk_factors.append(f"{intent.value} operations carry inherent risk")
        
        # Potential impact
        potential_impact = f"Could affect {len(affected_components)} components. "
        if overall_risk in ["critical", "high"]:
            potential_impact += "May cause service disruption or data inconsistency."
        else:
            potential_impact += "Impact likely limited to specific functionality."
        
        # Mitigation strategies
        mitigation_strategies = [
            "Implement comprehensive testing before deployment",
            "Use feature flags for gradual rollout",
            "Prepare rollback plan",
            "Monitor system metrics post-deployment"
        ]
        
        if repo_evidence.evidence_confidence < 0.7:
            mitigation_strategies.append("Perform additional manual code review")
        
        return RiskAssessment(
            overall_risk=overall_risk,
            risk_factors=risk_factors,
            probability_of_failure=probability_of_failure,
            potential_impact=potential_impact,
            mitigation_strategies=mitigation_strategies
        )
    
    def _generate_recommended_changes(
        self,
        intent: IntentType,
        target_name: str,
        repo_evidence: RepoEvidence,
        engine_result: Dict[str, Any]
    ) -> List[RecommendedChange]:
        """Generate recommended changes."""
        
        changes = []
        
        # Add changes based on intent
        if intent == IntentType.DELETE:
            changes.append(RecommendedChange(
                description=f"Remove {target_name} and all references",
                priority="critical",
                effort_estimate="2-4 hours",
                code_snippet=f"# TODO: Remove {target_name}"
            ))
        elif intent == IntentType.RENAME:
            changes.append(RecommendedChange(
                description=f"Rename {target_name} and update all references",
                priority="high",
                effort_estimate="1-2 hours"
            ))
        elif intent == IntentType.MODIFY:
            changes.append(RecommendedChange(
                description=f"Modify {target_name} according to requirements",
                priority="high",
                effort_estimate="2-3 hours"
            ))
        elif intent == IntentType.REFACTOR:
            changes.append(RecommendedChange(
                description=f"Refactor {target_name} to improve code quality",
                priority="medium",
                effort_estimate="4-6 hours"
            ))
        
        # Add changes for affected components
        for component in repo_evidence.classes[:5]:
            changes.append(RecommendedChange(
                description=f"Review and update {component.name} for compatibility",
                priority="medium",
                effort_estimate="30 minutes",
                file_path=component.file_path
            ))
        
        return changes
    
    def _generate_implementation_plan(
        self,
        intent: IntentType,
        target_name: str,
        repo_evidence: RepoEvidence,
        recommended_changes: List[RecommendedChange]
    ) -> ImplementationPlan:
        """Generate comprehensive implementation plan."""
        
        phases = ["Preparation", "Implementation", "Testing", "Deployment"]
        
        steps = []
        step_number = 1
        
        # Preparation phase
        steps.append(ImplementationStep(
            step_number=step_number,
            description="Create feature branch",
            action_type="git",
            target="repository",
            dependencies=[],
            estimated_time="5 minutes"
        ))
        step_number += 1
        
        steps.append(ImplementationStep(
            step_number=step_number,
            description=f"Backup current state of {target_name}",
            action_type="backup",
            target=target_name,
            dependencies=[str(step_number - 1)],
            estimated_time="10 minutes"
        ))
        step_number += 1
        
        # Implementation phase
        for i, change in enumerate(recommended_changes[:5], start=step_number):
            steps.append(ImplementationStep(
                step_number=i,
                description=change.description,
                action_type="code",
                target=change.file_path or target_name,
                dependencies=[str(i - 1)],
                estimated_time=change.effort_estimate
            ))
            step_number = i + 1
        
        # Testing phase
        steps.append(ImplementationStep(
            step_number=step_number,
            description="Run unit tests",
            action_type="test",
            target="codebase",
            dependencies=[str(step_number - 1)],
            estimated_time="15 minutes"
        ))
        step_number += 1
        
        steps.append(ImplementationStep(
            step_number=step_number,
            description="Run integration tests",
            action_type="test",
            target="codebase",
            dependencies=[str(step_number - 1)],
            estimated_time="20 minutes"
        ))
        step_number += 1
        
        # Deployment phase
        steps.append(ImplementationStep(
            step_number=step_number,
            description="Create pull request",
            action_type="git",
            target="repository",
            dependencies=[str(step_number - 1)],
            estimated_time="5 minutes"
        ))
        
        # Calculate total time
        total_hours = sum(
            self._parse_time_to_hours(step.estimated_time) for step in steps
        )
        total_estimated_time = f"{total_hours:.1f} hours"
        
        return ImplementationPlan(
            phases=phases,
            steps=steps,
            total_estimated_time=total_estimated_time,
            prerequisites=[
                "Write access to repository",
                "Local development environment set up",
                "Test database available"
            ],
            rollback_plan="Revert to previous commit using git revert or restore from backup"
        )
    
    def _parse_time_to_hours(self, time_str: str) -> float:
        """Parse time string to hours."""
        if "hour" in time_str.lower():
            return float(time_str.split()[0])
        elif "minute" in time_str.lower():
            return float(time_str.split()[0]) / 60
        return 0.5  # Default to 30 minutes
    
    def _generate_testing_checklist(
        self,
        intent: IntentType,
        target_name: str,
        repo_evidence: RepoEvidence,
        implementation_plan: ImplementationPlan
    ) -> TestingChecklist:
        """Generate comprehensive testing checklist."""
        
        unit_tests = [
            TestItem(
                description=f"Test {target_name} functionality",
                test_type="unit",
                priority="critical",
                automated=True,
                test_scope=target_name
            ),
            TestItem(
                description="Test error handling",
                test_type="unit",
                priority="high",
                automated=True,
                test_scope=target_name
            )
        ]
        
        integration_tests = [
            TestItem(
                description=f"Test {target_name} integration with dependencies",
                test_type="integration",
                priority="critical",
                automated=True,
                test_scope="component"
            )
        ]
        
        e2e_tests = [
            TestItem(
                description="Test end-to-end user flows",
                test_type="e2e",
                priority="high",
                automated=False,
                test_scope="system"
            )
        ]
        
        performance_tests = [
            TestItem(
                description="Test performance under load",
                test_type="performance",
                priority="medium",
                automated=True,
                test_scope="system"
            )
        ]
        
        security_tests = [
            TestItem(
                description="Test for security vulnerabilities",
                test_type="security",
                priority="high",
                automated=True,
                test_scope="codebase"
            )
        ]
        
        total_test_count = (
            len(unit_tests) + len(integration_tests) + 
            len(e2e_tests) + len(performance_tests) + len(security_tests)
        )
        
        return TestingChecklist(
            unit_tests=unit_tests,
            integration_tests=integration_tests,
            e2e_tests=e2e_tests,
            performance_tests=performance_tests,
            security_tests=security_tests,
            total_test_count=total_test_count,
            coverage_target=0.8
        )
    
    def _generate_engineering_actions(
        self,
        intent: IntentType,
        target_name: str,
        recommended_changes: List[RecommendedChange],
        implementation_plan: ImplementationPlan
    ) -> List[EngineeringAction]:
        """Generate actionable engineering steps."""
        
        actions = []
        
        # Add actions for recommended changes
        for change in recommended_changes[:3]:
            actions.append(EngineeringAction(
                action_type="code",
                description=change.description,
                file_path=change.file_path,
                priority=change.priority,
                owner="Developer"
            ))
        
        # Add testing actions
        actions.append(EngineeringAction(
            action_type="testing",
            description="Execute test suite",
            priority="critical",
            owner="QA Engineer"
        ))
        
        # Add documentation action
        actions.append(EngineeringAction(
            action_type="documentation",
            description=f"Update documentation for {target_name}",
            priority="medium",
            owner="Technical Writer"
        ))
        
        # Add deployment action
        actions.append(EngineeringAction(
            action_type="deployment",
            description="Deploy to staging environment",
            priority="high",
            owner="DevOps Engineer"
        ))
        
        return actions
