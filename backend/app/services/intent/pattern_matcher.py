"""
Pattern Matcher

Matches natural language questions against intent patterns using regex and keyword analysis.
Provides deterministic classification for common engineering question patterns.
"""

import re
import logging
from typing import Optional, Tuple, Dict, List
from .schemas import IntentType, TargetType

logger = logging.getLogger(__name__)


class PatternMatcher:
    """
    Matches questions against predefined patterns to determine intent.
    
    Uses regex patterns and keyword analysis to classify questions into:
    - EXPLAIN: "What does X do?", "How does Y work?"
    - DELETE: "Delete X", "Remove Y", "What happens if I delete Z?"
    - RENAME: "Rename X to Y", "Change name of Z"
    - REFACTOR: "Refactor X", "Improve Y", "Clean up Z"
    - ADD_FEATURE: "Add X feature", "Implement Y functionality"
    - DEPENDENCY: "What depends on X?", "Who uses Y?"
    - ARCHITECTURE: "Show me the architecture", "How is X connected?"
    - PLANNING: "How do I implement X?", "Plan for Y feature"
    """
    
    # Intent patterns with regex
    INTENT_PATTERNS = {
        IntentType.DELETE: [
            r'\b(delete|remove|drop|destroy|eliminate)\s+(?:the\s+)?(.+?)\b',
            r'\bwhat\s+(?:happens\s+)?if\s+(?:i\s+)?(?:delete|remove)\s+(?:the\s+)?(.+?)\b',
            r'\bimpact\s+of\s+(?:deleting|removing)\s+(?:the\s+)?(.+?)\b',
        ],
        IntentType.RENAME: [
            r'\brename\s+(.+?)\s+(?:to|as)\s+(.+?)\b',
            r'\bchange\s+(?:the\s+)?name\s+of\s+(.+?)\s+to\s+(.+?)\b',
            r'\bmove\s+(.+?)\s+to\s+(.+?)\b',
        ],
        IntentType.REFACTOR: [
            r'\brefactor\s+(.+?)\b',
            r'\bimprove\s+(.+?)\b',
            r'\bclean\s+up\s+(.+?)\b',
            r'\boptimize\s+(.+?)\b',
            r'\bsimplify\s+(.+?)\b',
        ],
        IntentType.ADD_FEATURE: [
            r'\badd\s+(.+?)\s+(?:feature|functionality|capability)\b',
            r'\bimplement\s+(.+?)\b',
            r'\bcreate\s+(.+?)\b',
            r'\bbuild\s+(.+?)\b',
        ],
        IntentType.DEPENDENCY: [
            r'\bwhat\s+(?:does\s+)?(.+?)\s+(?:depend\s+on|use|call|import)\b',
            r'\bwho\s+(?:uses|calls|depends\s+on)\s+(.+?)\b',
            r'\bwhat\s+(?:breaks|fails)\s+if\s+(?:i\s+)?(?:delete|change)\s+(.+?)\b',
            r'\bimpact\s+of\s+(?:changing|modifying)\s+(.+?)\b',
        ],
        IntentType.ARCHITECTURE: [
            r'\bshow\s+(?:me\s+)?(?:the\s+)?architecture\b',
            r'\bhow\s+(?:is|are)\s+(.+?)\s+(?:connected|structured|organized)\b',
            r'\b(?:visualize|display|draw)\s+(?:the\s+)?(?:architecture|structure)\b',
            r'\bwhat\s+(?:are\s+)?(?:the\s+)?(?:components|modules|services)\s+(?:in|of)\s+(.+?)\b',
        ],
        IntentType.PLANNING: [
            r'\bhow\s+(?:do\s+i|should\s+i|to)\s+(?:implement|build|create)\s+(.+?)\b',
            r'\bplan\s+(?:for|to)\s+(.+?)\b',
            r'\b(?:steps|approach|strategy)\s+(?:for|to)\s+(?:implement|build)\s+(.+?)\b',
            r'\bwhat\s+(?:are\s+)?(?:the\s+)?(?:requirements|prerequisites)\s+(?:for|to)\s+(.+?)\b',
        ],
        IntentType.EXPLAIN: [
            r'\bexplain\s+(.+?)\b',
            r'\bdescribe\s+(.+?)\b',
            r'\bhow\s+(?:does|do)\s+(.+?)\s+(?:work|function)\b',
            r'\bwhy\s+(?:does|is)\s+(.+?)\b',
        ],
    }
    
    # Keywords for quick classification
    INTENT_KEYWORDS = {
        IntentType.DELETE: ['delete', 'remove', 'drop', 'destroy', 'eliminate', 'impact of deleting'],
        IntentType.RENAME: ['rename', 'change name', 'move to', 'rename to'],
        IntentType.REFACTOR: ['refactor', 'improve', 'clean up', 'optimize', 'simplify'],
        IntentType.ADD_FEATURE: ['add', 'implement', 'create', 'build', 'add feature'],
        IntentType.DEPENDENCY: ['depend', 'uses', 'calls', 'imports', 'impact of changing', 'what breaks'],
        IntentType.ARCHITECTURE: ['architecture', 'structure', 'connected', 'components', 'modules', 'visualize'],
        IntentType.PLANNING: ['how to implement', 'plan for', 'steps to', 'approach for', 'strategy for'],
        IntentType.EXPLAIN: ['what does', 'how does', 'explain', 'describe', 'why does'],
    }
    
    def __init__(self):
        """Initialize the pattern matcher."""
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[IntentType, List[re.Pattern]]:
        """Pre-compile regex patterns for performance."""
        compiled = {}
        for intent_type, patterns in self.INTENT_PATTERNS.items():
            compiled[intent_type] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        return compiled
    
    def match(self, question: str) -> Tuple[Optional[IntentType], float]:
        """
        Match the question against intent patterns.
        
        Args:
            question: The normalized question text
            
        Returns:
            Tuple of (matched_intent_type, confidence_score) or (None, 0.0)
        """
        lower_question = question.lower()
        
        # Try regex patterns first (higher confidence)
        for intent_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(question):
                    logger.debug(f"Pattern matched: {intent_type} for question: {question}")
                    return intent_type, 0.85  # High confidence for pattern match
        
        # Fallback to keyword matching (lower confidence)
        for intent_type, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in lower_question:
                    # Calculate confidence based on keyword specificity
                    confidence = self._calculate_keyword_confidence(keyword, lower_question)
                    logger.debug(f"Keyword matched: {intent_type} (confidence: {confidence}) for question: {question}")
                    return intent_type, confidence
        
        logger.debug(f"No pattern matched for question: {question}")
        return None, 0.0
    
    def _calculate_keyword_confidence(self, keyword: str, question: str) -> float:
        """
        Calculate confidence score for keyword match.
        
        Args:
            keyword: The matched keyword
            question: The lowercased question
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_confidence = 0.6
        
        # Boost confidence for more specific keywords
        if len(keyword.split()) > 1:  # Multi-word keywords are more specific
            base_confidence += 0.15
        
        # Boost confidence if keyword appears at the start
        if question.startswith(keyword):
            base_confidence += 0.1
        
        # Cap at 0.8 (below pattern match confidence)
        return min(base_confidence, 0.8)
    
    def extract_target_from_pattern(self, question: str, intent_type: IntentType) -> Optional[str]:
        """
        Extract the target entity name from a matched pattern.
        
        Args:
            question: The normalized question
            intent_type: The matched intent type
            
        Returns:
            Extracted target name or None
        """
        if intent_type not in self._compiled_patterns:
            return None
        
        for pattern in self._compiled_patterns[intent_type]:
            match = pattern.search(question)
            if match:
                # Return the last captured group (usually the target)
                if match.lastindex:
                    return match.group(match.lastindex).strip()
        
        return None
