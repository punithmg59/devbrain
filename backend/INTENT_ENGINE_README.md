# Intent Engine

The Intent Engine is a reusable service for classifying user questions into structured intents. It serves as the first layer of the AI Change Intelligence system, ensuring that every question is properly categorized before being processed by downstream agents.

## Architecture

### Components

1. **Intent Models** (`app/models/intent.py`)
   - `Intent` enum: Defines all supported intent types (DELETE_CODE, ADD_FEATURE, MODIFY_CODE, etc.)
   - `TargetType` enum: Defines target types for code-related intents (service, component, module, etc.)

2. **Intent Schemas** (`app/schemas/intent.py`)
   - `IntentClassificationRequest`: Request schema with question and optional context
   - `IntentClassificationResponse`: Response schema with intent, target info, confidence, and method

3. **DeterministicParser** (`app/services/intent_engine.py`)
   - Lightweight regex-based parser for common patterns
   - Fast, deterministic classification with high confidence
   - Extracts target names and infers target types from context

4. **LLMClassifier** (`app/services/intent_engine.py`)
   - Fallback LLM-based classifier using Groq
   - Handles ambiguous or complex questions
   - Provides structured JSON output with confidence scores

5. **IntentEngine** (`app/services/intent_engine.py`)
   - Main service orchestrating classification
   - Tries deterministic parsing first (fast)
   - Falls back to LLM if confidence is low (< 0.75)
   - Ultimate fallback to GENERAL intent

## Usage

### Basic Usage

```python
from app.services.intent_engine import IntentEngine

engine = IntentEngine()
result = engine.classify("What breaks if I delete AuthService?")

# Returns:
# IntentClassificationResponse(
#     intent=Intent.DELETE_CODE,
#     target_type=TargetType.SERVICE,
#     target_name="AuthService",
#     feature=None,
#     confidence=0.95,
#     method="deterministic"
# )
```

### With Context

```python
result = engine.classify(
    "What is this?",
    context={"file": "app/services/auth.py"}
)
```

### Batch Classification

```python
questions = [
    "What breaks if I delete AuthService?",
    "Where should I add Stripe?",
    "How do I refactor this code?"
]
results = engine.classify_batch(questions)
```

## Supported Intents

- **DELETE_CODE**: Questions about deleting or removing code
- **ADD_FEATURE**: Questions about adding new features or integrations
- **MODIFY_CODE**: Questions about changing or updating existing code
- **REFACTOR**: Questions about code quality, cleanup, or restructuring
- **RENAME**: Questions about renaming code elements
- **MOVE**: Questions about moving code to different locations
- **DEBUG**: Questions about bugs, errors, or troubleshooting
- **ARCHITECTURE**: Questions about system design, structure, or patterns
- **DEPENDENCY**: Questions about libraries, packages, or requirements
- **DATABASE**: Questions about databases, schemas, or migrations
- **API**: Questions about APIs, endpoints, or routes
- **SECURITY**: Questions about authentication, authorization, or vulnerabilities
- **PERFORMANCE**: Questions about optimization, speed, or efficiency
- **TESTING**: Questions about tests, coverage, or specifications
- **GENERAL**: General questions that don't fit other categories

## Architecture Decisions

### 1. Two-Tier Classification Strategy

**Decision**: Use deterministic parsing first, LLM fallback second.

**Rationale**:
- Deterministic parsing is fast (milliseconds vs seconds)
- Reduces LLM API costs for common patterns
- Provides predictable, consistent results for standard questions
- LLM reserved for ambiguous/complex cases where it adds value

### 2. Confidence Threshold

**Decision**: Set confidence threshold at 0.75.

**Rationale**:
- High enough to ensure quality deterministic classifications
- Low enough to allow LLM fallback for edge cases
- Balances speed vs accuracy

### 3. Strongly Typed Models

**Decision**: Use Pydantic models with enums for all data structures.

**Rationale**:
- Type safety prevents invalid intents
- Self-documenting code
- Easy serialization/deserialization
- Validation at the boundary

### 4. Reusable Service Pattern

**Decision**: Create a standalone service, not embedded in routers.

**Rationale**:
- Future agents can reuse the engine
- Easy to test in isolation
- Can be used in multiple contexts (API, CLI, etc.)
- Follows single responsibility principle

### 5. Case Preservation

**Decision**: Preserve original case when extracting target names.

**Rationale**:
- "AuthService" is more useful than "authservice"
- Maintains fidelity to user's question
- Better for downstream processing

### 6. Target Type Inference

**Decision**: Infer target type from context clues in the question.

**Rationale**:
- Adds valuable metadata without extra user input
- Helps downstream agents understand the scope
- Uses simple pattern matching for speed

## Testing

Run the test suite:

```bash
python -m pytest tests/test_intent_engine.py -v
```

Test coverage includes:
- All 15 intent types
- Target type inference
- Case preservation
- Confidence thresholds
- Batch classification
- Schema validation
- Fallback behavior

## Integration with Future Agents

The Intent Engine is designed to be called by any agent before processing:

```python
# Example agent pattern
from app.services.intent_engine import IntentEngine

class SomeAgent:
    def __init__(self):
        self.intent_engine = IntentEngine()
    
    def process_question(self, question: str):
        # First, classify the intent
        intent_result = self.intent_engine.classify(question)
        
        # Then route based on intent
        if intent_result.intent == Intent.DELETE_CODE:
            return self.handle_delete(intent_result)
        elif intent_result.intent == Intent.ADD_FEATURE:
            return self.handle_add_feature(intent_result)
        # ... etc
```

## Performance

- **Deterministic parsing**: < 1ms per question
- **LLM classification**: ~500-2000ms per question (depends on model)
- **Overall**: ~90% of questions handled deterministically, ~10% require LLM

## Future Enhancements

Potential improvements:
- Add caching for repeated questions
- Implement confidence calibration
- Add support for multi-intent questions
- Include telemetry for pattern optimization
- Add custom pattern registration
