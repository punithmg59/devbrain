"""
Intent Engine Module

Converts natural-language engineering questions into strongly typed Intent objects.

This module provides the first layer of the AI Operating System, enabling
future engines (Root Cause Intelligence, PR Review, Security Review, Test Intelligence)
to understand and process user intent.
"""

from .intent_engine import IntentEngine
from .schemas import Intent, IntentType, TargetType, IntentRequest, IntentResponse

__all__ = ["IntentEngine", "Intent", "IntentType", "TargetType", "IntentRequest", "IntentResponse"]
