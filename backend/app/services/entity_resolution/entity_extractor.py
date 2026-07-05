"""Entity Extraction Service - Extracts engineering action and target from natural language."""

import re
from typing import Optional

from .models import EngineeringAction, EntityExtraction, TargetType


class EntityExtractor:
    """Extracts engineering action, target name, and target type from natural language queries."""

    # Action patterns
    ACTION_PATTERNS = {
        EngineeringAction.DELETE: [
            r'\bdelete\b',
            r'\bremove\b',
            r'\bdrop\b',
            r'\bget rid of\b',
            r'\beliminate\b'
        ],
        EngineeringAction.RENAME: [
            r'\brename\b',
            r'\bchange name of\b',
            r'\brename to\b'
        ],
        EngineeringAction.MOVE: [
            r'\bmove\b',
            r'\btransfer\b',
            r'\brelocate\b'
        ],
        EngineeringAction.ADD: [
            r'\badd\b',
            r'\bcreate\b',
            r'\bimplement\b',
            r'\bintegrate\b',
            r'\binstall\b'
        ],
        EngineeringAction.EXTRACT: [
            r'\bextract\b',
            r'\brefactor\b',
            r'\bsplit\b'
        ],
        EngineeringAction.EXPLAIN: [
            r'\bexplain\b',
            r'\bdescribe\b',
            r'\bwhat is\b',
            r'\bhow does\b',
            r'\bwhy\b'
        ],
        EngineeringAction.FIND: [
            r'\bfind\b',
            r'\blocate\b',
            r'\bsearch\b',
            r'\bwhere is\b',
            r'\bshow\b'
        ]
    }

    # Target type patterns
    TARGET_TYPE_PATTERNS = {
        TargetType.FUNCTION: [
            r'\(\)$',  # Ends with ()
            r'\bfunction\b',
            r'\bmethod\b'
        ],
        TargetType.CLASS: [
            r'\bclass\b',
            r'\b[A-Z][a-zA-Z]*\b'  # CamelCase
        ],
        TargetType.SERVICE: [
            r'\bservice\b',
            r'\bService$'
        ],
        TargetType.API: [
            r'\bapi\b',
            r'\bendpoint\b',
            r'\broute\b'
        ],
        TargetType.API_ROUTE: [
            r'\b/api/',
            r'\bendpoint\b'
        ],
        TargetType.DATABASE_TABLE: [
            r'\btable\b',
            r'\bmodel\b'
        ],
        TargetType.WORKFLOW: [
            r'\bworkflow\b',
            r'\bpipeline\b',
            r'\bjob\b'
        ],
        TargetType.FILE: [
            r'\.py$',
            r'\.js$',
            r'\.ts$',
            r'\.java$',
            r'\.go$',
            r'\bfile\b'
        ],
        TargetType.MODULE: [
            r'\bmodule\b',
            r'\bpackage\b'
        ]
    }

    def extract(self, query: str) -> EntityExtraction:
        """
        Extract engineering action, target name, and target type from natural language.

        Args:
            query: Natural language query (e.g., "Delete AuthService")

        Returns:
            EntityExtraction with extracted information
        """
        query = query.strip()
        action = self._extract_action(query)
        target_name = self._extract_target_name(query, action)
        target_type = self._infer_target_type(query, target_name)
        confidence = self._calculate_confidence(action, target_name, target_type)

        return EntityExtraction(
            action=action,
            target_name=target_name,
            target_type=target_type,
            raw_query=query,
            confidence=confidence
        )

    def _extract_action(self, query: str) -> Optional[EngineeringAction]:
        """Extract the engineering action from the query."""
        query_lower = query.lower()

        for action, patterns in self.ACTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return action

        return None

    def _extract_target_name(self, query: str, action: Optional[EngineeringAction]) -> Optional[str]:
        """Extract the target name from the query."""
        # Remove the action word and common stop words
        query_lower = query.lower()

        # Remove action words
        for action, patterns in self.ACTION_PATTERNS.items():
            for pattern in patterns:
                query_lower = re.sub(pattern, '', query_lower, flags=re.IGNORECASE)

        # Remove common stop words
        stop_words = ['the', 'a', 'an', 'to', 'from', 'for', 'with', 'by', 'on', 'in', 'at']
        for word in stop_words:
            query_lower = re.sub(rf'\b{word}\b', '', query_lower)

        # Clean up and extract the target
        target = query_lower.strip()

        # Remove trailing punctuation
        target = re.sub(r'[.,!?;:]+$', '', target)

        # If empty, try to extract from original query using heuristics
        if not target:
            # Try to find the last word or phrase that looks like a name
            words = query.split()
            if len(words) > 1:
                # Skip the first word (likely the action)
                target = ' '.join(words[1:])

        return target if target else None

    def _infer_target_type(self, query: str, target_name: Optional[str]) -> Optional[TargetType]:
        """Infer the target type from the query and target name."""
        if not target_name:
            return None

        query_lower = query.lower()
        target_lower = target_name.lower()

        # Check for explicit type mentions in query
        for target_type, patterns in self.TARGET_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return target_type

        # Infer from target name patterns
        if re.search(r'\(\)$', target_name):
            return TargetType.FUNCTION
        elif target_name.endswith('Service'):
            return TargetType.SERVICE
        elif target_name.endswith('Controller'):
            return TargetType.CLASS
        elif target_name.endswith('Repository'):
            return TargetType.CLASS
        elif target_name.endswith('Middleware'):
            return TargetType.CLASS
        elif target_name.endswith('Integration'):
            return TargetType.MODULE
        elif target_name.endswith('API'):
            return TargetType.API
        elif re.match(r'^[A-Z][a-zA-Z]+$', target_name):
            # CamelCase likely a class
            return TargetType.CLASS
        elif re.match(r'^[a-z_]+$', target_name):
            # snake_case likely a function or variable
            return TargetType.FUNCTION

        return TargetType.UNKNOWN

    def _calculate_confidence(
        self,
        action: Optional[EngineeringAction],
        target_name: Optional[str],
        target_type: Optional[TargetType]
    ) -> float:
        """Calculate confidence score for the extraction."""
        confidence = 0.0

        if action:
            confidence += 0.4
        if target_name:
            confidence += 0.4
        if target_type and target_type != TargetType.UNKNOWN:
            confidence += 0.2

        return min(confidence, 1.0)
