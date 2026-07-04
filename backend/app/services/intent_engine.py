import re
import json
from typing import Optional, Tuple
from groq import Groq
from app.models.intent import Intent, TargetType
from app.schemas.intent import IntentClassificationResponse
from app.config import get_settings


class DeterministicParser:
    """Lightweight deterministic parser for intent classification."""
    
    # Intent patterns with confidence scores
    PATTERNS = {
        Intent.DELETE_CODE: {
            'patterns': [
                r'\bdelete\b.*\b(\w+)\b',
                r'\bremove\b.*\b(\w+)\b',
                r'\bwhat breaks if i delete\b',
                r'\bwhat happens if i remove\b',
                r'\bcan i delete\b',
                r'\bshould i remove\b',
                r'\bimpact of deleting\b',
                r'\bimpact of removing\b',
            ],
            'confidence': 0.95,
            'extract_target': True
        },
        Intent.ADD_FEATURE: {
            'patterns': [
                r'\badd\b.*\b(\w+)\b',
                r'\bimplement\b.*\b(\w+)\b',
                r'\bwhere should i add\b',
                r'\bhow to add\b',
                r'\bintegrate\b.*\b(\w+)\b',
                r'\binstall\b.*\b(\w+)\b',
                r'\binclude\b.*\b(\w+)\b',
            ],
            'confidence': 0.90,
            'extract_target': True
        },
        Intent.MODIFY_CODE: {
            'patterns': [
                r'\bchange\b.*\b(\w+)\b',
                r'\bmodify\b.*\b(\w+)\b',
                r'\bupdate\b.*\b(\w+)\b',
                r'\bedit\b.*\b(\w+)\b',
                r'\bfix\b.*\b(\w+)\b',
                r'\balter\b.*\b(\w+)\b',
            ],
            'confidence': 0.85,
            'extract_target': True
        },
        Intent.REFACTOR: {
            'patterns': [
                r'\brefactor\b',
                r'\bclean up\b',
                r'\brestructure\b',
                r'\bimprove code\b',
                r'\bcode quality\b',
                r'\btechnical debt\b',
                r'\bsimplify\b',
            ],
            'confidence': 0.92,
            'extract_target': False
        },
        Intent.RENAME: {
            'patterns': [
                r'\brename\b.*\b(\w+)\b',
                r'\bwhat should i rename\b',
                r'\bbetter name for\b',
            ],
            'confidence': 0.90,
            'extract_target': True
        },
        Intent.MOVE: {
            'patterns': [
                r'\bmove\b.*\b(\w+)\b',
                r'\bwhere should i move\b',
                r'\brelocate\b',
            ],
            'confidence': 0.88,
            'extract_target': True
        },
        Intent.DEBUG: {
            'patterns': [
                r'\bdebug\b',
                r'\bfix bug\b',
                r'\btroubleshoot\b',
                r'\bwhy is\b',
                r'\berror\b',
                r'\bexception\b',
                r'\bnot working\b',
                r'\bbroken\b',
                r'\bissue\b',
            ],
            'confidence': 0.87,
            'extract_target': False
        },
        Intent.ARCHITECTURE: {
            'patterns': [
                r'\barchitecture\b',
                r'\bdesign\b',
                r'\bstructure\b',
                r'\bpattern\b',
                r'\bcomponent\b',
                r'\bmodule\b',
                r'\blayer\b',
                r'\bhigh level\b',
                r'\boverview\b',
            ],
            'confidence': 0.85,
            'extract_target': False
        },
        Intent.DEPENDENCY: {
            'patterns': [
                r'\bdependenc',
                r'\brequirement\b',
                r'\blibrary\b',
                r'\bpackage\b',
                r'\bimport\b',
                r'\bversion\b',
            ],
            'confidence': 0.83,
            'extract_target': False
        },
        Intent.DATABASE: {
            'patterns': [
                r'\bdatabase\b',
                r'\bdb\b',
                r'\bschema\b',
                r'\bmigration\b',
                r'\bquery\b',
                r'\bsql\b',
                r'\btable\b',
                r'\bmodel\b',
            ],
            'confidence': 0.86,
            'extract_target': False
        },
        Intent.API: {
            'patterns': [
                r'\bapi\b',
                r'\bendpoint\b',
                r'\broute\b',
                r'\brequest\b',
                r'\bresponse\b',
                r'\brest\b',
                r'\bgraphql\b',
                r'\bhttp\b',
            ],
            'confidence': 0.84,
            'extract_target': False
        },
        Intent.SECURITY: {
            'patterns': [
                r'\bsecurity\b',
                r'\bauthentication\b',
                r'\bauthorization\b',
                r'\bpermission\b',
                r'\bvulnerability\b',
                r'\bencrypt\b',
                r'\bsecure\b',
            ],
            'confidence': 0.88,
            'extract_target': False
        },
        Intent.PERFORMANCE: {
            'patterns': [
                r'\bperformance\b',
                r'\bslow\b',
                r'\bspeed\b',
                r'\blatency\b',
                r'\bthroughput\b',
                r'\befficient\b',
            ],
            'confidence': 0.85,
            'extract_target': False
        },
        Intent.TESTING: {
            'patterns': [
                r'\bunit tests?\b',
                r'\bintegration tests?\b',
                r'\bcoverage\b',
                r'\bspec\b',
                r'\bmock\b',
                r'\bassert\b',
                r'\btest case\b',
            ],
            'confidence': 0.86,
            'extract_target': False
        },
    }
    
    # Target type patterns
    TARGET_TYPE_PATTERNS = {
        TargetType.SERVICE: [r'\bservice\b', r'\bservice\b'],
        TargetType.COMPONENT: [r'\bcomponent\b', r'\bwidget\b', r'\belement\b'],
        TargetType.MODULE: [r'\bmodule\b', r'\bpackage\b'],
        TargetType.FUNCTION: [r'\bfunction\b', r'\bmethod\b', r'\bdef\b'],
        TargetType.CLASS: [r'\bclass\b', r'\btype\b'],
        TargetType.FILE: [r'\bfile\b', r'\.py\b', r'\.js\b', r'\.ts\b'],
        TargetType.VARIABLE: [r'\bvariable\b', r'\bvar\b', r'\blet\b', r'\bconst\b'],
        TargetType.INTERFACE: [r'\binterface\b', r'\bapi\b', r'\bcontract\b'],
        TargetType.MODEL: [r'\bmodel\b', r'\bschema\b', r'\bentity\b'],
        TargetType.ROUTE: [r'\broute\b', r'\bpath\b'],
        TargetType.ENDPOINT: [r'\bendpoint\b', r'\burl\b'],
    }
    
    @classmethod
    def parse(cls, question: str) -> Optional[Tuple[Intent, float, Optional[str], Optional[TargetType]]]:
        """
        Parse question using deterministic patterns.
        
        Returns:
            Tuple of (intent, confidence, target_name, target_type) or None if no match
        """
        question_lower = question.lower()
        
        for intent, config in cls.PATTERNS.items():
            for pattern in config['patterns']:
                match = re.search(pattern, question_lower, re.IGNORECASE)
                if match:
                    confidence = config['confidence']
                    target_name = None
                    target_type = None
                    
                    # Extract target if configured
                    if config['extract_target'] and match.groups():
                        # Extract from original question to preserve case
                        original_match = re.search(pattern, question, re.IGNORECASE)
                        if original_match and original_match.groups():
                            target_name = original_match.group(1).strip()
                        else:
                            target_name = match.group(1).strip()
                        target_type = cls._infer_target_type(question_lower, target_name)
                    
                    return (intent, confidence, target_name, target_type)
        
        return None
    
    @classmethod
    def _infer_target_type(cls, question: str, target_name: str) -> Optional[TargetType]:
        """Infer target type from context."""
        question_lower = question.lower()
        
        for target_type, patterns in cls.TARGET_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    return target_type
        
        return TargetType.UNKNOWN


class LLMClassifier:
    """LLM-based classifier for fallback when deterministic parsing fails."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = Groq(api_key=self.settings.groq_api_key)
        self.model = "llama-3.3-70b-versatile"
    
    SYSTEM_PROMPT = """You are an intent classifier for a code intelligence system. 
Classify the user's question into one of these intents:

DELETE_CODE - Questions about deleting or removing code
ADD_FEATURE - Questions about adding new features or integrations
MODIFY_CODE - Questions about changing or updating existing code
REFACTOR - Questions about code quality, cleanup, or restructuring
RENAME - Questions about renaming code elements
MOVE - Questions about moving code to different locations
DEBUG - Questions about bugs, errors, or troubleshooting
ARCHITECTURE - Questions about system design, structure, or patterns
DEPENDENCY - Questions about libraries, packages, or requirements
DATABASE - Questions about databases, schemas, or migrations
API - Questions about APIs, endpoints, or routes
SECURITY - Questions about authentication, authorization, or vulnerabilities
PERFORMANCE - Questions about optimization, speed, or efficiency
TESTING - Questions about tests, coverage, or specifications
GENERAL - General questions that don't fit other categories

Return ONLY valid JSON with this exact structure:
{
  "intent": "INTENT_NAME",
  "target_type": "service|component|module|function|class|file|variable|interface|model|route|endpoint|unknown|null",
  "target_name": "extracted name or null",
  "feature": "feature name for ADD_FEATURE or null",
  "confidence": 0.0-1.0
}

Do not include any explanation or extra text."""
    
    def classify(self, question: str, context: Optional[dict] = None) -> Optional[Tuple[Intent, float, Optional[str], Optional[TargetType], Optional[str]]]:
        """
        Classify question using LLM.
        
        Returns:
            Tuple of (intent, confidence, target_name, target_type, feature) or None if classification fails
        """
        try:
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Question: {question}"}
            ]
            
            if context:
                messages[1]["content"] += f"\nContext: {json.dumps(context, indent=2)}"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            intent = Intent(result.get("intent", "GENERAL"))
            confidence = float(result.get("confidence", 0.7))
            target_name = result.get("target_name")
            target_type = TargetType(result.get("target_type", "unknown")) if result.get("target_type") else None
            feature = result.get("feature")
            
            return (intent, confidence, target_name, target_type, feature)
            
        except Exception as e:
            # Log error in production
            return None


class IntentEngine:
    """
    Main Intent Engine service that combines deterministic parsing and LLM fallback.
    
    This service provides a reusable interface for classifying user questions into
    structured intents. It uses lightweight deterministic parsing first, and only
    falls back to LLM classification when confidence is low or no pattern matches.
    """
    
    CONFIDENCE_THRESHOLD = 0.75
    
    def __init__(self):
        self.parser = DeterministicParser()
        self.llm_classifier = LLMClassifier()
    
    def classify(self, question: str, context: Optional[dict] = None) -> IntentClassificationResponse:
        """
        Classify a user question into a structured intent.
        
        Args:
            question: The user's natural language question
            context: Optional context about the codebase
            
        Returns:
            IntentClassificationResponse with classified intent and metadata
        """
        # Try deterministic parsing first
        deterministic_result = self.parser.parse(question)
        
        if deterministic_result:
            intent, confidence, target_name, target_type = deterministic_result
            
            # If confidence is high enough, return deterministic result
            if confidence >= self.CONFIDENCE_THRESHOLD:
                return IntentClassificationResponse(
                    intent=intent,
                    target_type=target_type,
                    target_name=target_name,
                    feature=None,
                    confidence=confidence,
                    method="deterministic"
                )
        
        # Fall back to LLM classification
        llm_result = self.llm_classifier.classify(question, context)
        
        if llm_result:
            intent, confidence, target_name, target_type, feature = llm_result
            return IntentClassificationResponse(
                intent=intent,
                target_type=target_type,
                target_name=target_name,
                feature=feature,
                confidence=confidence,
                method="llm"
            )
        
        # Ultimate fallback to GENERAL with low confidence
        return IntentClassificationResponse(
            intent=Intent.GENERAL,
            target_type=None,
            target_name=None,
            feature=None,
            confidence=0.5,
            method="fallback"
        )
    
    def classify_batch(self, questions: list[str], context: Optional[dict] = None) -> list[IntentClassificationResponse]:
        """
        Classify multiple questions in batch.
        
        Args:
            questions: List of user questions
            context: Optional context about the codebase
            
        Returns:
            List of IntentClassificationResponse objects
        """
        return [self.classify(q, context) for q in questions]
