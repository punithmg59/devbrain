"""
Confidence Engine

Calculates and validates confidence scores for intent classification.
Determines when LLM fallback is required based on configurable thresholds.
"""

import logging
from typing import Dict, List, Optional
from .schemas import IntentType, TargetType

logger = logging.getLogger(__name__)


class ConfidenceEngine:
    """
    Calculates and validates confidence scores for intent classification.
    
    The confidence engine evaluates:
    - Pattern match confidence
    - Entity extraction confidence
    - Overall classification confidence
    - Whether LLM fallback is required
    
    Confidence thresholds are configurable for different scenarios.
    """
    
    # Default confidence thresholds
    DEFAULT_LLM_THRESHOLD = 0.6
    DEFAULT_HIGH_CONFIDENCE_THRESHOLD = 0.8
    DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.4
    
    # Intent-specific thresholds (can override defaults)
    INTENT_THRESHOLDS = {
        IntentType.DELETE: 0.7,  # Higher threshold for destructive operations
        IntentType.RENAME: 0.65,
        IntentType.REFACTOR: 0.6,
        IntentType.ADD_FEATURE: 0.5,
        IntentType.DEPENDENCY: 0.6,
        IntentType.ARCHITECTURE: 0.5,
        IntentType.PLANNING: 0.5,
        IntentType.EXPLAIN: 0.4,
        IntentType.UNKNOWN: 0.0,  # Always use LLM for unknown
    }
    
    def __init__(
        self,
        llm_threshold: float = DEFAULT_LLM_THRESHOLD,
        high_confidence_threshold: float = DEFAULT_HIGH_CONFIDENCE_THRESHOLD,
        low_confidence_threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD
    ):
        """
        Initialize the confidence engine.
        
        Args:
            llm_threshold: Confidence threshold below which LLM is required
            high_confidence_threshold: Threshold for high confidence classification
            low_confidence_threshold: Threshold for low confidence classification
        """
        self.llm_threshold = llm_threshold
        self.high_confidence_threshold = high_confidence_threshold
        self.low_confidence_threshold = low_confidence_threshold
    
    def calculate_overall_confidence(
        self,
        pattern_confidence: float,
        entity_confidence: float,
        intent_type: IntentType,
        target_type: TargetType
    ) -> float:
        """
        Calculate overall confidence from component scores.
        
        Args:
            pattern_confidence: Confidence from pattern matching
            entity_confidence: Confidence from entity extraction
            intent_type: The classified intent type
            target_type: The classified target type
            
        Returns:
            Overall confidence score between 0.0 and 1.0
        """
        # Weight pattern matching higher than entity extraction
        combined = 0.7 * pattern_confidence + 0.3 * entity_confidence
        
        # Adjust based on intent type
        intent_adjustment = self._get_intent_adjustment(intent_type)
        combined += intent_adjustment
        
        # Adjust based on target type specificity
        target_adjustment = self._get_target_adjustment(target_type)
        combined += target_adjustment
        
        # Ensure within bounds
        return max(0.0, min(combined, 1.0))
    
    def _get_intent_adjustment(self, intent_type: IntentType) -> float:
        """
        Get confidence adjustment based on intent type.
        
        Args:
            intent_type: The classified intent type
            
        Returns:
            Adjustment value between -0.1 and +0.1
        """
        # Boost confidence for intents with clear patterns
        if intent_type in [IntentType.DELETE, IntentType.DEPENDENCY]:
            return 0.05
        elif intent_type in [IntentType.EXPLAIN, IntentType.ARCHITECTURE]:
            return 0.0
        elif intent_type == IntentType.UNKNOWN:
            return -0.1
        return 0.0
    
    def _get_target_adjustment(self, target_type: TargetType) -> float:
        """
        Get confidence adjustment based on target type.
        
        Args:
            target_type: The classified target type
            
        Returns:
            Adjustment value between -0.1 and +0.1
        """
        # Boost confidence for specific, well-defined targets
        if target_type in [TargetType.SERVICE, TargetType.CLASS, TargetType.API]:
            return 0.05
        elif target_type == TargetType.UNKNOWN:
            return -0.1
        return 0.0
    
    def requires_llm(
        self,
        confidence: float,
        intent_type: IntentType
    ) -> bool:
        """
        Determine if LLM fallback is required.
        
        Args:
            confidence: The overall confidence score
            intent_type: The classified intent type
            
        Returns:
            True if LLM fallback is required
        """
        # Always use LLM for unknown intents
        if intent_type == IntentType.UNKNOWN:
            return True
        
        # Use intent-specific threshold if available
        threshold = self.INTENT_THRESHOLDS.get(intent_type, self.llm_threshold)
        
        # Use LLM if confidence is below threshold
        return confidence < threshold
    
    def get_confidence_level(self, confidence: float) -> str:
        """
        Get human-readable confidence level.
        
        Args:
            confidence: The confidence score
            
        Returns:
            String representation of confidence level
        """
        if confidence >= self.high_confidence_threshold:
            return "HIGH"
        elif confidence >= self.llm_threshold:
            return "MEDIUM"
        elif confidence >= self.low_confidence_threshold:
            return "LOW"
        else:
            return "VERY_LOW"
    
    def validate_confidence(
        self,
        confidence: float,
        intent_type: IntentType,
        target_type: TargetType
    ) -> Dict[str, any]:
        """
        Validate confidence score and provide diagnostic information.
        
        Args:
            confidence: The confidence score to validate
            intent_type: The classified intent type
            target_type: The classified target type
            
        Returns:
            Dictionary with validation results
        """
        level = self.get_confidence_level(confidence)
        requires_llm = self.requires_llm(confidence, intent_type)
        
        validation = {
            "confidence": confidence,
            "level": level,
            "requires_llm": requires_llm,
            "threshold": self.INTENT_THRESHOLDS.get(intent_type, self.llm_threshold),
            "intent_type": intent_type,
            "target_type": target_type,
            "is_valid": confidence >= 0.0 and confidence <= 1.0,
        }
        
        if not validation["is_valid"]:
            validation["error"] = "Confidence score must be between 0.0 and 1.0"
        
        return validation
    
    def adjust_confidence_for_context(
        self,
        confidence: float,
        context: Dict[str, any]
    ) -> float:
        """
        Adjust confidence based on additional context.
        
        Args:
            confidence: The base confidence score
            context: Additional context information
            
        Returns:
            Adjusted confidence score
        """
        adjusted = confidence
        
        # Boost confidence if we have repository context
        if context.get("has_repository_context"):
            adjusted += 0.05
        
        # Boost confidence if target was found in repository
        if context.get("target_found_in_repo"):
            adjusted += 0.1
        
        # Reduce confidence if question is ambiguous
        if context.get("is_ambiguous"):
            adjusted -= 0.15
        
        # Reduce confidence if multiple possible targets
        if context.get("multiple_possible_targets"):
            adjusted -= 0.1
        
        return max(0.0, min(adjusted, 1.0))
