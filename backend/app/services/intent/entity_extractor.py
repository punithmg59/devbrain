"""
Entity Extractor

Extracts named entities from natural language engineering questions.
Identifies target names and their types (service, class, function, etc.).
"""

import re
import logging
from typing import List, Optional, Tuple
from .schemas import ExtractedEntity, TargetType

logger = logging.getLogger(__name__)


class EntityExtractor:
    """
    Extracts entities from natural language questions.
    
    Uses pattern matching and heuristics to identify:
    - Service names (AuthService, PaymentService)
    - Class names (User, OrderController)
    - Function names (processPayment, validateUser)
    - File names (auth.py, user.service.ts)
    - API endpoints (/api/users, POST /login)
    - Database tables (users, orders)
    """
    
    # Patterns for different entity types
    PATTERNS = {
        TargetType.SERVICE: [
            r'\b([A-Z][a-zA-Z0-9]*Service)\b',  # AuthService
            r'\b([A-Z][a-zA-Z0-9]*Manager)\b',  # UserManager
            r'\b([A-Z][a-zA-Z0-9]*Handler)\b',  # RequestHandler
        ],
        TargetType.CLASS: [
            r'\b([A-Z][a-zA-Z0-9]{2,})\b',  # PascalCase class names (min 3 chars)
        ],
        TargetType.FUNCTION: [
            r'\b([a-z][a-zA-Z0-9]{3,})\b',  # camelCase function names (min 4 chars)
        ],
        TargetType.FILE: [
            r'\b([a-zA-Z0-9_\-]+\.(py|ts|js|java|go|rs|cpp|h))\b',  # file extensions
        ],
        TargetType.API: [
            r'\b([A-Z]+\s+/[a-zA-Z0-9_\-/]+)\b',  # POST /api/users
            r'\b(/[a-zA-Z0-9_\-/]+)\b',  # /api/users
        ],
        TargetType.DATABASE_TABLE: [
            r'\b([a-z][a-z0-9_]{2,})\s+table\b',  # users table (min 3 chars)
            r'\btable\s+([a-z][a-z0-9_]{2,})\b',  # table users (min 3 chars)
        ],
        TargetType.MODULE: [
            r'\b([a-z][a-z0-9_]{2,})\s+module\b',  # auth module (min 3 chars)
            r'\bmodule\s+([a-z][a-z0-9_]{2,})\b',  # module auth (min 3 chars)
        ],
    }
    
    # Keywords that indicate specific types
    TYPE_KEYWORDS = {
        TargetType.SERVICE: ['service', 'manager', 'handler', 'provider'],
        TargetType.CLASS: ['class', 'object', 'instance'],
        TargetType.FUNCTION: ['function', 'method', 'procedure'],
        TargetType.FILE: ['file', 'document'],
        TargetType.API: ['endpoint', 'route', 'api', 'rest'],
        TargetType.DATABASE_TABLE: ['table', 'collection'],
        TargetType.WORKFLOW: ['workflow', 'pipeline', 'job'],
        TargetType.MODULE: ['module', 'package', 'library'],
    }
    
    # Common words to exclude from entity extraction
    COMMON_WORDS = {
        'what', 'does', 'how', 'why', 'where', 'when', 'who', 'which', 'the', 'a', 'an',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
        'must', 'can', 'need', 'want', 'like', 'use', 'make', 'take', 'get',
        'give', 'go', 'come', 'see', 'know', 'think', 'look', 'want', 'give',
        'use', 'find', 'tell', 'ask', 'work', 'seem', 'feel', 'try', 'leave',
        'call', 'delete', 'remove', 'add', 'create', 'build', 'implement', 'explain',
        'describe', 'show', 'change', 'rename', 'refactor', 'improve', 'optimize',
        'plan', 'implement', 'depends', 'on', 'to', 'for', 'with', 'at', 'from',
        'by', 'about', 'against', 'between', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on',
        'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there',
        'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
        'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
        'so', 'than', 'too', 'very', 'just', 'also', 'now', 'it', 'its', 'this',
        'that', 'these', 'those', 'he', 'she', 'they', 'we', 'you', 'me', 'him',
        'her', 'them', 'us', 'my', 'your', 'his', 'her', 'their', 'our', 'mine',
        'yours', 'hers', 'theirs', 'ours', 'myself', 'yourself', 'himself', 'herself',
        'itself', 'ourselves', 'yourselves', 'themselves'
    }
    
    def __init__(self):
        """Initialize the entity extractor."""
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> dict:
        """Pre-compile regex patterns for performance."""
        compiled = {}
        for target_type, patterns in self.PATTERNS.items():
            compiled[target_type] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        return compiled
    
    def extract(self, question: str) -> List[ExtractedEntity]:
        """
        Extract entities from the question.
        
        Args:
            question: The normalized question text
            
        Returns:
            List of extracted entities with confidence scores
        """
        entities = []
        seen_positions = set()  # Track positions to avoid overlapping matches
        
        # Priority order for pattern matching (most specific first)
        priority_order = [
            TargetType.SERVICE,
            TargetType.FILE,
            TargetType.API,
            TargetType.DATABASE_TABLE,
            TargetType.MODULE,
            TargetType.CLASS,
            TargetType.FUNCTION,
        ]
        
        # Try each pattern type in priority order
        for target_type in priority_order:
            if target_type not in self._compiled_patterns:
                continue
            patterns = self._compiled_patterns[target_type]
            for pattern in patterns:
                matches = pattern.finditer(question)
                for match in matches:
                    # Skip if this position is already covered
                    match_key = (match.start(), match.end())
                    if match_key in seen_positions:
                        continue
                    
                    entity_name = match.group(1) if match.lastindex and match.group(1) else match.group(0)
                    
                    # Skip common words
                    if entity_name.lower() in self.COMMON_WORDS:
                        continue
                    
                    # Calculate confidence based on pattern specificity
                    confidence = self._calculate_confidence(entity_name, target_type, question)
                    
                    # Only include if confidence is above threshold
                    if confidence >= 0.3:
                        entity = ExtractedEntity(
                            name=entity_name,
                            type=target_type,
                            confidence=confidence,
                            start_position=match.start(),
                            end_position=match.end()
                        )
                        entities.append(entity)
                        seen_positions.add(match_key)
        
        # Remove duplicates and keep highest confidence
        entities = self._deduplicate_entities(entities)
        
        logger.debug(f"Extracted {len(entities)} entities from question: {question}")
        return entities
    
    def _calculate_confidence(self, entity_name: str, target_type: TargetType, question: str) -> float:
        """
        Calculate confidence score for an extracted entity.
        
        Args:
            entity_name: The extracted entity name
            target_type: The classified target type
            question: The original question
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.5  # Base confidence
        
        # Boost confidence based on naming conventions
        if target_type == TargetType.SERVICE:
            if entity_name.endswith('Service'):
                confidence += 0.3
            elif entity_name.endswith('Manager'):
                confidence += 0.25
            elif entity_name.endswith('Handler'):
                confidence += 0.2
        elif target_type == TargetType.CLASS:
            if entity_name[0].isupper() and len(entity_name) > 2:
                confidence += 0.3
        elif target_type == TargetType.FUNCTION:
            if entity_name[0].islower():
                confidence += 0.2
        elif target_type == TargetType.FILE:
            if '.' in entity_name:
                confidence += 0.3
        elif target_type == TargetType.API:
            if entity_name.startswith('/'):
                confidence += 0.4
        
        # Check for contextual keywords
        lower_question = question.lower()
        for keyword in self.TYPE_KEYWORDS.get(target_type, []):
            if keyword in lower_question:
                confidence += 0.1
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    def _deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """
        Remove duplicate entities, keeping the highest confidence version.
        
        Args:
            entities: List of extracted entities
            
        Returns:
            Deduplicated list of entities
        """
        entity_map = {}
        
        for entity in entities:
            key = (entity.name.lower(), str(entity.type))
            if key not in entity_map or entity.confidence > entity_map[key].confidence:
                entity_map[key] = entity
        
        return list(entity_map.values())
    
    def extract_primary_target(self, question: str) -> Tuple[Optional[str], Optional[TargetType]]:
        """
        Extract the primary target from the question.
        
        Args:
            question: The normalized question
            
        Returns:
            Tuple of (target_name, target_type) or (None, None)
        """
        entities = self.extract(question)
        
        if not entities:
            return None, None
        
        # Return the entity with highest confidence
        primary = max(entities, key=lambda e: e.confidence)
        return primary.name, primary.type
