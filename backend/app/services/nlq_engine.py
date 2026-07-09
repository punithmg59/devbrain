"""
Natural Language Question Engine

Main orchestration layer for processing natural language engineering questions.
Integrates with existing Intent Engine, Entity Resolution, Reference Intelligence,
Engineering Evidence, Reasoning, and Simulation engines.

All AI responses are grounded in repository data using the EngineeringEvidence system.
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from .intent.intent_engine import IntentEngine
from .intent.schemas import IntentRequest, IntentResponse, IntentType
from .entity_resolution.entity_resolver import EntityResolver
from .reference_intelligence.reference_intelligence_engine import ReferenceIntelligenceEngine
from .engineering_evidence.engineering_evidence_engine import EngineeringEvidenceEngine
from .engineering_evidence.repository_data_collector import RepositoryDataCollector
from .engineering_evidence.models import EngineeringEvidence
from .engineering_intelligence_service import EngineeringIntelligenceService
from .impact_analysis_engine import ImpactAnalysisEngine
from .reasoning.reasoning_engine import ReasoningEngine
from .simulation_engine import ChangeSimulationEngine
from ..utils.validation import validate_engineering_evidence
from ..utils.logging_config import get_logger, log_performance
from ..utils.exceptions import NLQEngineError, EvidenceValidationError
from ..utils.pipeline_errors import pipeline_stage, PipelineStageError, build_error_response

logger = get_logger(__name__)


class NLQEngine:
    """
    Natural Language Question Engine for DevBrain.
    
    This engine serves as the main entry point for natural language queries,
    orchestrating the existing backend engines to provide comprehensive answers.
    
    Pipeline:
    1. Classify intent using existing Intent Engine
    2. Extract and resolve repository entities using Entity Resolution
    3. Collect comprehensive repository evidence (AST, dependencies, call graph, etc.)
    4. Build structured EngineeringEvidence object
    5. Route to appropriate backend engine with evidence context
    6. Validate all responses are grounded in repository data
    7. Add limitation statements if evidence is missing
    8. Aggregate and return results
    """
    
    def __init__(self, db: Optional[AsyncSession] = None):
        """Initialize the NLQ Engine with all required sub-engines."""
        self.intent_engine = IntentEngine()
        self.entity_resolver = EntityResolver()
        self.reference_intelligence = ReferenceIntelligenceEngine()
        self.engineering_evidence_engine = EngineeringEvidenceEngine()
        self.repository_data_collector = RepositoryDataCollector()
        self.engineering_intelligence_service = EngineeringIntelligenceService()
        self.impact_analysis = ImpactAnalysisEngine()
        self.reasoning_engine = ReasoningEngine()
        self.simulation_engine = ChangeSimulationEngine()
        self.db = db
        
        logger.info("NLQ Engine initialized with all sub-engines including repository-aware evidence collection and engineering intelligence")
    
    async def process_question(self, repo_id: str, question: str, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """
        Process a natural language engineering question with repository-aware reasoning.

        Every pipeline stage is wrapped in a structured error handler that:
        - Logs the full traceback to the backend log.
        - Returns a clean {success: false, stage: ...} dict on failure.
        - Never raises raw exceptions to the router.

        Args:
            repo_id: The repository ID
            question: The natural language question
            db: Database session for evidence collection

        Returns:
            Dictionary containing the answer and metadata, or a PipelineError dict.
        """
        import uuid as _uuid
        correlation_id = str(_uuid.uuid4())
        logger.info(f"[{correlation_id}] Processing question for repo_id={repo_id}: {question}")

        db_session = db or self.db

        # ── Stage 1: Intent Classification ────────────────────────────────
        intent_request = IntentRequest(repo_id=repo_id, question=question)
        intent = None
        intent_response = None
        try:
            async with pipeline_stage("intent_engine", correlation_id):
                intent_response = self.intent_engine.classify(intent_request)
                intent = intent_response.intent
                logger.info(
                    f"[{correlation_id}] Intent: {intent.intent}, "
                    f"target: {intent.target_name}, confidence: {intent.confidence:.2f}"
                )
        except PipelineStageError as exc:
            return build_error_response(exc.payload)

        # ── Stage 2: Entity Resolution ────────────────────────────────────
        resolved_entities: Dict[str, Any] = {"primary_target": None, "related_entities": []}
        try:
            async with pipeline_stage("entity_resolution", correlation_id):
                resolved_entities = self._resolve_entities(repo_id=repo_id, intent=intent)
        except PipelineStageError as exc:
            # Non-fatal: proceed with empty resolution
            logger.warning(f"[{correlation_id}] Entity resolution failed — continuing with empty entities")

        # ── Stage 3: Engineering Evidence Collection ───────────────────────
        engineering_evidence = None
        try:
            async with pipeline_stage("engineering_evidence", correlation_id):
                engineering_evidence = await self._collect_engineering_evidence(
                    repo_id=repo_id,
                    intent=intent,
                    resolved_entities=resolved_entities,
                    db=db_session
                )
        except PipelineStageError as exc:
            return build_error_response(exc.payload)

        # ── Stage 4: Evidence Validation ──────────────────────────────────
        validation_result = {"is_valid": True, "has_limitations": False, "errors": []}
        try:
            async with pipeline_stage("evidence_validation", correlation_id):
                evidence_validation = validate_engineering_evidence(engineering_evidence, strict=False)
                if not evidence_validation["is_valid"]:
                    logger.warning(
                        f"[{correlation_id}] Evidence validation: "
                        f"{len(evidence_validation['errors'])} errors"
                    )
                validation_result = self._validate_evidence(engineering_evidence)
        except PipelineStageError as exc:
            # Non-fatal: proceed with degraded evidence
            logger.warning(f"[{correlation_id}] Evidence validation failed — proceeding with degraded evidence")

        # ── Stage 5: Engine Routing / Reasoning ───────────────────────────
        result: Dict[str, Any] = {"answer": "", "evidence": None, "processing_time_ms": 0}
        try:
            async with pipeline_stage("reasoning", correlation_id):
                result = self._route_to_engine(
                    repo_id=repo_id,
                    intent=intent,
                    resolved_entities=resolved_entities,
                    engineering_evidence=engineering_evidence
                )
                if validation_result["has_limitations"]:
                    result["answer"] = self._add_limitation_context(
                        result["answer"],
                        engineering_evidence.limitations
                    )
        except PipelineStageError as exc:
            return build_error_response(exc.payload)

        # ── Stage 6: Report / Engineering Intelligence Composer ───────────
        try:
            async with pipeline_stage("report_composer", correlation_id):
                engineering_intelligence = self.engineering_intelligence_service.generate_intelligence_response(
                    question=question,
                    intent=intent.intent,
                    target_name=intent.target_name,
                    repo_evidence=engineering_evidence,
                    engine_result=result
                )
                response = engineering_intelligence.dict()
        except PipelineStageError as exc:
            return build_error_response(exc.payload)

        # ── Assemble final response ────────────────────────────────────────
        response["success"] = True
        response["correlation_id"] = correlation_id
        response["confidence"] = intent.confidence
        response["reasoning"] = intent.reasoning
        response["extracted_entities"] = [
            {
                "name": entity.name,
                "type": entity.type.value if hasattr(entity.type, "value") else str(entity.type),
                "confidence": entity.confidence,
            }
            for entity in intent.extracted_entities
        ]
        response["resolved_entities"] = resolved_entities
        response["processing_time_ms"] = (
            (intent_response.processing_time_ms if intent_response else 0)
            + result.get("processing_time_ms", 0)
        )
        response["requires_llm"] = intent.requires_llm

        logger.info(
            f"[{correlation_id}] Question processed in {response['processing_time_ms']:.2f}ms "
            f"| evidence_confidence={engineering_evidence.evidence_confidence:.2f} "
            f"| grounded={validation_result['is_valid']}"
        )
        return response
    
    def _resolve_entities(self, repo_id: str, intent) -> Dict[str, Any]:
        """
        Resolve extracted entities to repository nodes.
        
        Args:
            repo_id: The repository ID
            intent: The classified intent
            
        Returns:
            Dictionary of resolved entities
        """
        resolved_entities = {
            "primary_target": None,
            "related_entities": []
        }
        
        try:
            # Resolve primary target
            if intent.target_name and intent.target_name != "unknown":
                primary_resolved = self.entity_resolver.resolve(
                    repo_id=repo_id,
                    entity_name=intent.target_name,
                    entity_type=intent.target_type
                )
                resolved_entities["primary_target"] = primary_resolved
            
            # Resolve additional extracted entities
            for entity in intent.extracted_entities:
                if entity.name.lower() != intent.target_name.lower():
                    resolved = self.entity_resolver.resolve(
                        repo_id=repo_id,
                        entity_name=entity.name,
                        entity_type=entity.type
                    )
                    if resolved:
                        resolved_entities["related_entities"].append(resolved)
            
            logger.info(f"Resolved {len(resolved_entities['related_entities']) + (1 if resolved_entities['primary_target'] else 0)} entities")
        except Exception as e:
            logger.error(f"Error resolving entities: {e}")
        
        return resolved_entities
    
    async def _collect_engineering_evidence(
        self,
        repo_id: str,
        intent,
        resolved_entities: Dict[str, Any],
        db: Optional[AsyncSession]
    ) -> EngineeringEvidence:
        """
        Collect comprehensive repository evidence for AI reasoning.
        
        Args:
            repo_id: The repository ID
            intent: The classified intent
            resolved_entities: Resolved repository entities
            db: Database session
            
        Returns:
            EngineeringEvidence object with all repository data
        """
        logger.info(f"Collecting engineering evidence for repo {repo_id}")
        
        try:
            repo_uuid = UUID(repo_id) if isinstance(repo_id, str) else repo_id
        except ValueError:
            # If repo_id is not a valid UUID, create a placeholder
            logger.warning(f"Invalid repo_id format: {repo_id}, using placeholder")
            repo_uuid = UUID('00000000-0000-0000-0000-000000000000')
        
        # Collect repository data
        repository_data = await self.repository_data_collector.collect_repository_data(
            repo_id=repo_uuid,
            repo_path="",  # Would need to fetch from Repo model
            target_name=intent.target_name if intent.target_name != "unknown" else None,
            db=db
        )
        
        # Create EngineeringEvidence object
        engineering_evidence = EngineeringEvidence(
            target_id=repo_uuid,
            target_name=intent.target_name,
            target_type=intent.target_type.value if hasattr(intent.target_type, 'value') else str(intent.target_type),
            repo_id=repo_uuid,
            ast_nodes=repository_data['ast_nodes'],
            dependency_graph=repository_data['dependency_graph'],
            call_graph=repository_data['call_graph'],
            classes=repository_data['classes'],
            functions=repository_data['functions'],
            api_routes=repository_data['api_routes'],
            imports=repository_data['imports'],
            overall_summary=f"Repository evidence collected for {intent.target_name}",
            evidence_confidence=0.0  # Will be calculated
        )
        
        # Calculate metrics and completeness
        engineering_evidence.calculate_overall_metrics()
        engineering_evidence.calculate_data_completeness()
        engineering_evidence.generate_limitation_statements()
        
        logger.info(f"Engineering evidence collected: confidence={engineering_evidence.evidence_confidence:.2f}")
        logger.info(f"  - AST nodes: {len(engineering_evidence.ast_nodes)}")
        logger.info(f"  - Classes: {len(engineering_evidence.classes)}")
        logger.info(f"  - Functions: {len(engineering_evidence.functions)}")
        logger.info(f"  - API routes: {len(engineering_evidence.api_routes)}")
        logger.info(f"  - Imports: {len(engineering_evidence.imports)}")
        
        return engineering_evidence
    
    def _validate_evidence(self, engineering_evidence: EngineeringEvidence) -> Dict[str, Any]:
        """
        Validate that evidence is grounded in repository data.
        
        Args:
            engineering_evidence: The engineering evidence to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "is_valid": True,
            "has_limitations": False,
            "errors": []
        }
        
        # Check evidence confidence
        if engineering_evidence.evidence_confidence < 0.3:
            validation_result["is_valid"] = False
            validation_result["errors"].append(
                f"Low evidence confidence: {engineering_evidence.evidence_confidence:.2f}"
            )
        
        # Check for missing critical data types
        critical_data_types = ['ast_nodes', 'functions', 'imports']
        for data_type in critical_data_types:
            completeness = engineering_evidence.data_completeness.get(data_type, 0.0)
            if completeness < 0.3:
                validation_result["has_limitations"] = True
                validation_result["errors"].append(
                    f"Low {data_type} completeness: {completeness:.2f}"
                )
        
        # Check if there are any limitations
        if engineering_evidence.limitations:
            validation_result["has_limitations"] = True
        
        logger.info(f"Evidence validation: valid={validation_result['is_valid']}, "
                   f"has_limitations={validation_result['has_limitations']}")
        
        return validation_result
    
    def _add_limitation_context(self, answer: str, limitations: List[str]) -> str:
        """
        Add limitation context to the answer.
        
        Args:
            answer: The original answer
            limitations: List of limitation statements
            
        Returns:
            Answer with limitation context added
        """
        if not limitations:
            return answer
        
        limitation_text = "\n\n**Limitations:**\n" + "\n".join(f"- {limit}" for limit in limitations)
        return answer + limitation_text
    
    def _route_to_engine(
        self,
        repo_id: str,
        intent,
        resolved_entities: Dict[str, Any],
        engineering_evidence: EngineeringEvidence
    ) -> Dict[str, Any]:
        """
        Route the question to the appropriate backend engine based on intent.
        
        Args:
            repo_id: The repository ID
            intent: The classified intent
            resolved_entities: Resolved repository entities
            
        Returns:
            Result from the appropriate engine
        """
        intent_type = intent.intent
        
        # Map intents to appropriate engines
        if intent_type in [IntentType.DELETE, IntentType.MODIFY, IntentType.MOVE]:
            return self._handle_change_intent(repo_id, intent, resolved_entities, engineering_evidence)
        elif intent_type == IntentType.RENAME:
            return self._handle_rename_intent(repo_id, intent, resolved_entities, engineering_evidence)
        elif intent_type in [IntentType.DEPENDENCY, IntentType.DEPENDENCY_QUERY]:
            return self._handle_dependency_intent(repo_id, intent, resolved_entities, engineering_evidence)
        elif intent_type == IntentType.REPOSITORY_QUERY:
            return self._handle_repository_query(repo_id, intent, resolved_entities, engineering_evidence)
        elif intent_type in [IntentType.ARCHITECTURE, IntentType.ARCHITECTURE_GUIDANCE]:
            return self._handle_architecture_intent(repo_id, intent, resolved_entities, engineering_evidence)
        elif intent_type == IntentType.FEATURE_PLANNING:
            return self._handle_feature_planning(repo_id, intent, resolved_entities, engineering_evidence)
        elif intent_type in [IntentType.REFACTOR, IntentType.REFACTORING_GUIDANCE]:
            return self._handle_refactoring_intent(repo_id, intent, resolved_entities, engineering_evidence)
        elif intent_type == IntentType.EXPLAIN:
            return self._handle_explain_intent(repo_id, intent, resolved_entities, engineering_evidence)
        else:
            return self._handle_general_intent(repo_id, intent, resolved_entities, engineering_evidence)
    
    def _handle_change_intent(
        self,
        repo_id: str,
        intent,
        resolved_entities: Dict[str, Any],
        engineering_evidence: EngineeringEvidence
    ) -> Dict[str, Any]:
        """
        Handle change-related intents (DELETE, MODIFY, MOVE).
        
        Uses Impact Analysis Engine to determine impact of changes.
        """
        logger.info(f"Handling change intent: {intent.intent}")
        
        try:
            # Use Impact Analysis Engine with repository evidence
            impact_result = self.impact_analysis.analyze_impact(
                repo_id=repo_id,
                target_name=intent.target_name,
                target_type=intent.target_type,
                change_type=intent.intent.value if hasattr(intent.intent, 'value') else str(intent.intent),
                engineering_evidence=engineering_evidence
            )
            
            # Ensure answer is grounded in evidence
            answer = impact_result.get("summary", "")
            if engineering_evidence.evidence_confidence < 0.5:
                answer += f"\n\nNote: Analysis based on limited repository evidence (confidence: {engineering_evidence.evidence_confidence:.2f})."
            
            return {
                "answer": answer,
                "evidence": impact_result.get("evidence"),
                "processing_time_ms": impact_result.get("processing_time_ms", 0)
            }
        except Exception as e:
            logger.error(f"Error in impact analysis: {e}")
            return {
                "answer": f"Error analyzing impact: {str(e)}",
                "evidence": None,
                "processing_time_ms": 0
            }
    
    def _handle_rename_intent(
        self,
        repo_id: str,
        intent,
        resolved_entities: Dict[str, Any],
        engineering_evidence: EngineeringEvidence
    ) -> Dict[str, Any]:
        """
        Handle RENAME intent.
        
        Uses Reference Intelligence to find all references that need updating.
        """
        logger.info(f"Handling rename intent: {intent.intent}")
        
        try:
            # Use Reference Intelligence Engine with repository evidence
            references = self.reference_intelligence.find_references(
                repo_id=repo_id,
                entity_name=intent.target_name,
                entity_type=intent.target_type,
                engineering_evidence=engineering_evidence
            )
            
            answer = f"Found {len(references)} references to {intent.target_name}. "
            answer += "These would need to be updated after renaming."
            
            # Add evidence confidence context
            if engineering_evidence.evidence_confidence < 0.5:
                answer += f"\n\nNote: Reference analysis based on limited repository evidence (confidence: {engineering_evidence.evidence_confidence:.2f})."
            
            return {
                "answer": answer,
                "evidence": {"references": references},
                "processing_time_ms": 0
            }
        except Exception as e:
            logger.error(f"Error finding references: {e}")
            return {
                "answer": f"Error finding references: {str(e)}",
                "evidence": None,
                "processing_time_ms": 0
            }
    
    def _handle_dependency_intent(
        self,
        repo_id: str,
        intent,
        resolved_entities: Dict[str, Any],
        engineering_evidence: EngineeringEvidence
    ) -> Dict[str, Any]:
        """
        Handle DEPENDENCY and DEPENDENCY_QUERY intents.
        
        Uses Engineering Evidence Engine to analyze dependencies.
        """
        logger.info(f"Handling dependency intent: {intent.intent}")
        
        try:
            # Use Engineering Evidence Engine
            dependencies = self.engineering_evidence_engine.analyze_dependencies(
                repo_id=repo_id,
                entity_name=intent.target_name,
                entity_type=intent.target_type
            )
            
            answer = f"{intent.target_name} depends on {len(dependencies.get('upstream', []))} components "
            answer += f"and is depended on by {len(dependencies.get('downstream', []))} components."
            
            return {
                "answer": answer,
                "evidence": dependencies,
                "processing_time_ms": 0
            }
        except Exception as e:
            logger.error(f"Error analyzing dependencies: {e}")
            return {
                "answer": f"Error analyzing dependencies: {str(e)}",
                "evidence": None,
                "processing_time_ms": 0
            }
    
    def _handle_repository_query(
        self,
        repo_id: str,
        intent,
        resolved_entities: Dict[str, Any],
        engineering_evidence: EngineeringEvidence
    ) -> Dict[str, Any]:
        """
        Handle REPOSITORY_QUERY intent.
        
        Provides overview of repository structure and components.
        """
        logger.info(f"Handling repository query intent: {intent.intent}")
        
        try:
            # Use Engineering Evidence Engine for repository overview
            overview = self.engineering_evidence_engine.get_repository_overview(repo_id=repo_id)
            
            answer = f"Repository contains {overview.get('total_files', 0)} files, "
            answer += f"{overview.get('total_services', 0)} services, "
            answer += f"and {overview.get('total_classes', 0)} classes."
            
            return {
                "answer": answer,
                "evidence": overview,
                "processing_time_ms": 0
            }
        except Exception as e:
            logger.error(f"Error getting repository overview: {e}")
            return {
                "answer": f"Error getting repository overview: {str(e)}",
                "evidence": None,
                "processing_time_ms": 0
            }
    
    def _handle_architecture_intent(
        self,
        repo_id: str,
        intent,
        resolved_entities: Dict[str, Any],
        engineering_evidence: EngineeringEvidence
    ) -> Dict[str, Any]:
        """
        Handle ARCHITECTURE and ARCHITECTURE_GUIDANCE intents.
        
        Uses Reference Intelligence and Reasoning engines.
        """
        logger.info(f"Handling architecture intent: {intent.intent}")
        
        try:
            # Use Reference Intelligence for architecture analysis
            architecture = self.reference_intelligence.analyze_architecture(
                repo_id=repo_id,
                focus_entity=intent.target_name if intent.target_name != "unknown" else None
            )
            
            # Use Reasoning Engine for guidance
            if intent.intent == IntentType.ARCHITECTURE_GUIDANCE:
                guidance = self.reasoning_engine.provide_architecture_guidance(
                    repo_id=repo_id,
                    context=architecture
                )
                answer = guidance.get("recommendation", "Architecture analysis complete")
            else:
                answer = architecture.get("summary", "Architecture analysis complete")
            
            return {
                "answer": answer,
                "evidence": architecture,
                "processing_time_ms": 0
            }
        except Exception as e:
            logger.error(f"Error in architecture analysis: {e}")
            return {
                "answer": f"Error in architecture analysis: {str(e)}",
                "evidence": None,
                "processing_time_ms": 0
            }
    
    def _handle_feature_planning(
        self,
        repo_id: str,
        intent,
        resolved_entities: Dict[str, Any],
        engineering_evidence: EngineeringEvidence
    ) -> Dict[str, Any]:
        """
        Handle FEATURE_PLANNING intent.
        
        Uses Reasoning Engine to provide implementation guidance.
        """
        logger.info(f"Handling feature planning intent: {intent.intent}")
        
        try:
            # Use Reasoning Engine for feature planning
            plan = self.reasoning_engine.plan_feature(
                repo_id=repo_id,
                feature_description=intent.target_name,
                context=resolved_entities
            )
            
            answer = f"Implementation plan for {intent.target_name}: "
            answer += plan.get("summary", "See evidence for detailed steps")
            
            return {
                "answer": answer,
                "evidence": plan,
                "processing_time_ms": 0
            }
        except Exception as e:
            logger.error(f"Error in feature planning: {e}")
            return {
                "answer": f"Error in feature planning: {str(e)}",
                "evidence": None,
                "processing_time_ms": 0
            }
    
    def _handle_refactoring_intent(
        self, 
        repo_id: str,
        intent,
        resolved_entities: Dict[str, Any],
        engineering_evidence: EngineeringEvidence
    ) -> Dict[str, Any]:
        """
        Handle REFACTOR and REFACTORING_GUIDANCE intents.
        
        Uses Reference Intelligence and Simulation engines.
        """
        logger.info(f"Handling refactoring intent: {intent.intent}")
        
        try:
            # Use Reference Intelligence for code analysis
            code_analysis = self.reference_intelligence.analyze_code(
                repo_id=repo_id,
                entity_name=intent.target_name,
                entity_type=intent.target_type
            )
            
            # Use Simulation Engine to validate refactoring approach
            if intent.intent == IntentType.REFACTORING_GUIDANCE:
                simulation = self.simulation_engine.simulate_refactoring(
                    repo_id=repo_id,
                    target=intent.target_name,
                    analysis=code_analysis
                )
                answer = simulation.get("recommendation", "Refactoring analysis complete")
                evidence = simulation
            else:
                answer = code_analysis.get("summary", "Code analysis complete")
                evidence = code_analysis
            
            return {
                "answer": answer,
                "evidence": evidence,
                "processing_time_ms": 0
            }
        except Exception as e:
            logger.error(f"Error in refactoring analysis: {e}")
            return {
                "answer": f"Error in refactoring analysis: {str(e)}",
                "evidence": None,
                "processing_time_ms": 0
            }
    
    def _handle_explain_intent(
        self,
        repo_id: str,
        intent,
        resolved_entities: Dict[str, Any],
        engineering_evidence: EngineeringEvidence
    ) -> Dict[str, Any]:
        """
        Handle EXPLAIN intent.
        
        Uses Reference Intelligence to explain code/components.
        """
        logger.info(f"Handling explain intent: {intent.intent}")
        
        try:
            # Use Reference Intelligence for explanation
            explanation = self.reference_intelligence.explain(
                repo_id=repo_id,
                entity_name=intent.target_name,
                entity_type=intent.target_type
            )
            
            answer = explanation.get("explanation", f"{intent.target_name} is a {intent.target_type}")
            
            return {
                "answer": answer,
                "evidence": explanation,
                "processing_time_ms": 0
            }
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return {
                "answer": f"Error generating explanation: {str(e)}",
                "evidence": None,
                "processing_time_ms": 0
            }
    
    def _handle_general_intent(
        self,
        repo_id: str,
        intent,
        resolved_entities: Dict[str, Any],
        engineering_evidence: EngineeringEvidence
    ) -> Dict[str, Any]:
        """
        Handle GENERAL or UNKNOWN intents.
        
        Provides a generic response or requests clarification.
        """
        logger.info(f"Handling general intent: {intent.intent}")
        
        answer = f"I understood your question about {intent.target_name}, "
        answer += f"but I'm not sure how to help with that specific request. "
        answer += "Try asking about deleting, renaming, moving, modifying, "
        answer += "dependencies, architecture, or refactoring."
        
        return {
            "answer": answer,
            "evidence": None,
            "processing_time_ms": 0
        }
