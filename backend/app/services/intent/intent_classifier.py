"""
Intent Classifier

Combines pattern matching and entity extraction to classify engineering questions.
Determines the primary intent and target type from natural language input.
"""

import logging
from typing import Optional, Tuple
from .schemas import IntentType, TargetType
from .pattern_matcher import PatternMatcher
from .entity_extractor import EntityExtractor

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Classifies the intent of natural language engineering questions.
    
    Combines pattern matching and entity extraction to determine:
    - The primary intent (DELETE, EXPLAIN, etc.)
    - The target type (SERVICE, CLASS, etc.)
    - The target name (AuthService, User, etc.)
    
    This classifier uses deterministic methods and does not require LLM calls
    for common patterns. LLM fallback is handled by the confidence engine.
    """
    
    def __init__(self):
        """Initialize the intent classifier."""
        self.pattern_matcher = PatternMatcher()
        self.entity_extractor = EntityExtractor()
    
    def classify(
        self,
        question: str
    ) -> Tuple[IntentType, TargetType, str, float]:
        """
        Classify the intent of a question.
        
        Args:
            question: The normalized question text
            
        Returns:
            Tuple of (intent_type, target_type, target_name, confidence)
        """
        # Step 1: Match intent patterns
        intent_type, pattern_confidence = self.pattern_matcher.match(question)
        
        if intent_type is None:
            intent_type = IntentType.UNKNOWN
            pattern_confidence = 0.0
        
        # Step 2: Extract entities
        target_name, target_type = self.entity_extractor.extract_primary_target(question)
        
        if target_name is None:
            target_name = "unknown"
        if target_type is None:
            target_type = TargetType.UNKNOWN
        
        # Step 3: Adjust confidence based on entity extraction
        entity_confidence = self._calculate_entity_confidence(target_name, target_type, question)
        
        # Combine confidences
        overall_confidence = self._combine_confidences(pattern_confidence, entity_confidence)
        
        logger.info(
            f"Classified: intent={intent_type}, target_type={target_type}, "
            f"target_name={target_name}, confidence={overall_confidence:.2f}"
        )
        
        return intent_type, target_type, target_name, overall_confidence
    
    def _calculate_entity_confidence(
        self,
        target_name: str,
        target_type: TargetType,
        question: str
    ) -> float:
        """
        Calculate confidence based on entity extraction quality.
        
        Args:
            target_name: The extracted target name
            target_type: The extracted target type
            question: The original question
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if target_type == TargetType.UNKNOWN or target_name == "unknown":
            return 0.3  # Low confidence if no entity found
        
        confidence = 0.7  # Base confidence for entity extraction
        
        # Boost confidence for specific target types
        if target_type in [TargetType.SERVICE, TargetType.CLASS, TargetType.API]:
            confidence += 0.15
        elif target_type in [TargetType.FUNCTION, TargetType.METHOD]:
            confidence += 0.1
        
        # Check if target name appears in question (should always be true)
        if target_name.lower() in question.lower():
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _combine_confidences(self, pattern_conf: float, entity_conf: float) -> float:
        """
        Combine pattern and entity confidences into overall confidence.
        
        Args:
            pattern_conf: Confidence from pattern matching
            entity_conf: Confidence from entity extraction
            
        Returns:
            Combined confidence score
        """
        # Weight pattern matching higher than entity extraction
        weights = [0.7, 0.3]
        confidences = [pattern_conf, entity_conf]
        
        combined = sum(w * c for w, c in zip(weights, confidences))
        return min(combined, 1.0)
    
    def determine_requires_graph(self, intent_type: IntentType, target_type: TargetType) -> bool:
        """
        Determine if graph traversal is required for this intent.
        
        Args:
            intent_type: The classified intent type
            target_type: The classified target type
            
        Returns:
            True if graph traversal is required
        """
        # These intents typically require graph analysis
        graph_required_intents = {
            IntentType.DELETE,
            IntentType.DEPENDENCY,
            IntentType.DEPENDENCY_QUERY,
            IntentType.REFACTOR,
            IntentType.REFACTORING_GUIDANCE,
            IntentType.ARCHITECTURE,
            IntentType.ARCHITECTURE_GUIDANCE,
            IntentType.MOVE,
            IntentType.MODIFY,
        }
        
        return intent_type in graph_required_intents
    
    def determine_requires_llm(self, confidence: float, intent_type: IntentType) -> bool:
        """
        Determine if LLM fallback is required based on confidence.
        
        Args:
            confidence: The overall confidence score
            intent_type: The classified intent type
            
        Returns:
            True if LLM fallback is required
        """
        # LLM threshold is configurable (default: 0.6)
        LLM_CONFIDENCE_THRESHOLD = 0.6
        
        # Always use LLM for unknown intents
        if intent_type == IntentType.UNKNOWN:
            return True
        
        # Use LLM if confidence is below threshold
        return confidence < LLM_CONFIDENCE_THRESHOLD
