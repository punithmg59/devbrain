"""
Intent Engine

Main orchestration layer for intent classification.
Converts natural-language engineering questions into strongly typed Intent objects.
"""

import logging
import time
from typing import Dict, Optional
from .schemas import Intent, IntentType, TargetType, IntentRequest, IntentResponse
from .entity_extractor import EntityExtractor
from .pattern_matcher import PatternMatcher
from .intent_classifier import IntentClassifier
from .confidence_engine import ConfidenceEngine

logger = logging.getLogger(__name__)


class IntentEngine:
    """
    Main Intent Engine for classifying natural language engineering questions.
    
    The Intent Engine is the first layer of the AI Operating System, converting
    user questions into structured Intent objects that can be processed by
    downstream engines (Root Cause Intelligence, PR Review, Security Review, etc.).
    
    Pipeline:
    1. Normalize the question
    2. Extract entities
    3. Pattern matching
    4. Intent classification
    5. Confidence calculation
    6. Determine if LLM fallback is required
    7. Return Intent object
    """
    
    def __init__(
        self,
        llm_confidence_threshold: float = 0.6,
        enable_llm_fallback: bool = True
    ):
        """
        Initialize the Intent Engine.
        
        Args:
            llm_confidence_threshold: Confidence threshold below which LLM is required
            enable_llm_fallback: Whether to enable LLM fallback for low confidence
        """
        self.entity_extractor = EntityExtractor()
        self.pattern_matcher = PatternMatcher()
        self.intent_classifier = IntentClassifier()
        self.confidence_engine = ConfidenceEngine(llm_threshold=llm_confidence_threshold)
        self.enable_llm_fallback = enable_llm_fallback
        
        logger.info(
            f"IntentEngine initialized with LLM threshold={llm_confidence_threshold}, "
            f"LLM fallback={'enabled' if enable_llm_fallback else 'disabled'}"
        )
    
    def classify(self, request: IntentRequest) -> IntentResponse:
        """
        Classify the intent of a natural language question.
        
        Args:
            request: The intent classification request
            
        Returns:
            IntentResponse with the classified intent and processing time
        """
        start_time = time.time()
        
        logger.info(f"Classifying intent for repo_id={request.repo_id}, question={request.question}")
        
        # Step 1: Normalize the question
        normalized_question = self._normalize_question(request.question)
        
        # Step 2: Extract entities
        extracted_entities = self.entity_extractor.extract(normalized_question)
        
        # Step 3: Classify intent
        intent_type, target_type, target_name, base_confidence = self.intent_classifier.classify(
            normalized_question
        )
        
        # Step 4: Calculate overall confidence
        matched_intent, pattern_confidence = self.pattern_matcher.match(normalized_question)
        entity_confidence = self._calculate_entity_confidence(extracted_entities)
        
        overall_confidence = self.confidence_engine.calculate_overall_confidence(
            pattern_confidence=pattern_confidence if pattern_confidence else 0.0,
            entity_confidence=entity_confidence,
            intent_type=intent_type,
            target_type=target_type
        )
        
        # Step 5: Determine if graph traversal is required
        requires_graph = self.intent_classifier.determine_requires_graph(intent_type, target_type)
        
        # Step 6: Determine if LLM fallback is required
        requires_llm = self.confidence_engine.requires_llm(overall_confidence, intent_type)
        
        # If LLM fallback is disabled but would be required, log a warning
        if requires_llm and not self.enable_llm_fallback:
            logger.warning(
                f"LLM fallback would be required (confidence={overall_confidence:.2f}) "
                f"but is disabled. Proceeding with deterministic classification."
            )
            requires_llm = False
        
        # Step 7: Build reasoning
        reasoning = self._build_reasoning(
            intent_type=intent_type,
            target_type=target_type,
            target_name=target_name,
            confidence=overall_confidence,
            requires_llm=requires_llm
        )
        
        # Step 8: Create Intent object
        intent = Intent(
            intent=intent_type,
            target_type=target_type,
            target_name=target_name,
            confidence=overall_confidence,
            requires_graph=requires_graph,
            requires_llm=requires_llm,
            extracted_entities=extracted_entities,
            raw_question=request.question,
            normalized_question=normalized_question,
            reasoning=reasoning
        )
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Intent classified in {processing_time_ms:.2f}ms: "
            f"intent={intent_type}, target={target_name}, confidence={overall_confidence:.2f}"
        )
        
        return IntentResponse(intent=intent, processing_time_ms=processing_time_ms)
    
    def _normalize_question(self, question: str) -> str:
        """
        Normalize the question for processing.
        
        Args:
            question: The raw question
            
        Returns:
            Normalized question
        """
        # Remove extra whitespace
        normalized = " ".join(question.split())
        
        # Remove common filler words at the start
        filler_prefixes = ["can you", "could you", "please", "i want to", "i need to"]
        for prefix in filler_prefixes:
            if normalized.lower().startswith(prefix):
                normalized = normalized[len(prefix):].strip()
                # Fix capitalization
                normalized = normalized[0].upper() + normalized[1:] if normalized else normalized
        
        return normalized
    
    def _calculate_entity_confidence(self, extracted_entities) -> float:
        """
        Calculate confidence based on entity extraction.
        
        Args:
            extracted_entities: List of extracted entities
            
        Returns:
            Entity confidence score
        """
        if not extracted_entities:
            return 0.3
        
        # Use the highest confidence entity
        max_confidence = max(entity.confidence for entity in extracted_entities)
        return max_confidence
    
    def _build_reasoning(
        self,
        intent_type: IntentType,
        target_type: TargetType,
        target_name: str,
        confidence: float,
        requires_llm: bool
    ) -> str:
        """
        Build human-readable reasoning for the classification.
        
        Args:
            intent_type: The classified intent type
            target_type: The classified target type
            target_name: The target name
            confidence: The confidence score
            requires_llm: Whether LLM fallback is required
            
        Returns:
            Human-readable reasoning string
        """
        confidence_level = self.confidence_engine.get_confidence_level(confidence)
        
        # Handle both enum and string types
        intent_str = intent_type.value if hasattr(intent_type, 'value') else str(intent_type)
        target_str = target_type.value if hasattr(target_type, 'value') else str(target_type)
        
        reasoning_parts = [
            f"Classified as {intent_str} intent targeting {target_str} '{target_name}'.",
            f"Confidence: {confidence:.2f} ({confidence_level})."
        ]
        
        if requires_llm:
            reasoning_parts.append(
                "LLM fallback is recommended due to low confidence or ambiguous input."
            )
        
        return " ".join(reasoning_parts)
    
    def classify_simple(self, repo_id: str, question: str) -> Intent:
        """
        Simplified classification method that returns just the Intent object.
        
        Args:
            repo_id: The repository ID
            question: The natural language question
            
        Returns:
            The classified Intent object
        """
        request = IntentRequest(repo_id=repo_id, question=question)
        response = self.classify(request)
        return response.intent
