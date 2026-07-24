"""
analysis/function_call_detection/call_classifier.py
----------------------------------------------------
Phase 4.7.2 — Function Call Classifier Engine.

Classifies every detected call invocation into one of 10 call types:
FUNCTION, METHOD, ASYNC, CONSTRUCTOR, CLASS_METHOD, STATIC_METHOD,
SUPER, LAMBDA, CALLABLE_OBJECT, UNKNOWN.

Design Principles
-----------------
- **Deterministic Heuristics & Symbol Table Awareness**: Uses syntactic form
  (e.g., `super()...`, `await ...`, dot notation, uppercase convention) as well
  as `SymbolTable` metadata (`SymbolKind.CLASS`, `@classmethod`, `@staticmethod`).
- **Non-Throwing**: Safely degrades to `CallType.UNKNOWN` or `CallType.FUNCTION`
  on ambiguous AST nodes.
"""

from __future__ import annotations

from typing import Optional, Set

from models.call_models import CallType
from models.symbol import Symbol, SymbolKind
from analysis.symbol_table.symbol_table import SymbolTable


class CallClassifier:
    """
    Classifier engine for determining the call type of a call expression.

    Usage::

        classifier = CallClassifier()
        call_type, flags = classifier.classify(callee_name, is_async, callee_symbol)
    """

    def classify(
        self,
        callee_name: str,
        is_async: bool = False,
        callee_symbol: Optional[Symbol] = None,
        enclosing_class: Optional[str] = None,
    ) -> CallClassificationResult:
        """
        Classify a call expression into a CallType and boolean flags.

        Parameters
        ----------
        callee_name:
            Raw callee expression string (e.g. 'login', 'user.login', 'User', 'super().__init__').
        is_async:
            True if the call is awaited (`await ...`).
        callee_symbol:
            Bound target symbol from SymbolTable if resolved.
        enclosing_class:
            Enclosing class name of caller scope if applicable.

        Returns
        -------
        CallClassificationResult
            Dataclass/named tuple containing assigned CallType and boolean flags.
        """
        name = (callee_name or "").strip()

        # 1. Super Call: e.g. super().__init__(), super().save()
        if name.startswith("super(") or name.startswith("super()."):
            return CallClassificationResult(
                call_type=CallType.SUPER,
                is_super_call=True,
                is_method=True,
                is_async=is_async,
            )

        # 2. Check Symbol Table Metadata if available
        if callee_symbol:
            # Callee is a Class symbol → Constructor Call
            if callee_symbol.kind == SymbolKind.CLASS:
                return CallClassificationResult(
                    call_type=CallType.CONSTRUCTOR,
                    is_constructor=True,
                    is_async=is_async,
                )

            # Callee is a Method symbol
            if callee_symbol.kind == SymbolKind.METHOD:
                modifiers = callee_symbol.metadata.get("method_modifiers", [])
                decorators = callee_symbol.metadata.get("decorators", [])
                dec_names = [d.get("name", "") if isinstance(d, dict) else str(d) for d in decorators]

                if "classmethod" in modifiers or any("classmethod" in d for d in dec_names):
                    return CallClassificationResult(
                        call_type=CallType.CLASS_METHOD,
                        is_classmethod=True,
                        is_method=True,
                        is_async=is_async or callee_symbol.metadata.get("is_async", False),
                    )

                if "staticmethod" in modifiers or any("staticmethod" in d for d in dec_names):
                    return CallClassificationResult(
                        call_type=CallType.STATIC_METHOD,
                        is_staticmethod=True,
                        is_method=True,
                        is_async=is_async or callee_symbol.metadata.get("is_async", False),
                    )

                # Standard instance method call or async method
                if is_async or callee_symbol.metadata.get("is_async", False):
                    return CallClassificationResult(
                        call_type=CallType.ASYNC,
                        is_async=True,
                        is_method=True,
                    )

                return CallClassificationResult(
                    call_type=CallType.METHOD,
                    is_method=True,
                    is_async=is_async,
                )

            # Callee is a Function symbol
            if callee_symbol.kind == SymbolKind.FUNCTION:
                if callee_symbol.metadata.get("is_lambda") or callee_symbol.name == "<lambda>":
                    return CallClassificationResult(
                        call_type=CallType.LAMBDA,
                        is_lambda=True,
                        is_async=is_async,
                    )

                if is_async or callee_symbol.metadata.get("is_async", False):
                    return CallClassificationResult(
                        call_type=CallType.ASYNC,
                        is_async=True,
                    )

                return CallClassificationResult(
                    call_type=CallType.FUNCTION,
                    is_async=is_async,
                )

        # 3. Syntactic Classification (when Symbol is not resolved or before resolution)

        # Async Call
        if is_async:
            is_method_call = "." in name and not self._is_constructor_name(name)
            return CallClassificationResult(
                call_type=CallType.ASYNC,
                is_async=True,
                is_method=is_method_call,
            )

        # Constructor Call: e.g. User(), FastAPI(), MyClass()
        if self._is_constructor_name(name):
            return CallClassificationResult(
                call_type=CallType.CONSTRUCTOR,
                is_constructor=True,
            )

        # Method Call or Class/Static Method: e.g. user.login(), Math.add(), User.build()
        if "." in name:
            parts = name.split(".")
            receiver = parts[0]
            # Receiver is Capitalized (Class.method) → ClassMethod / StaticMethod candidate
            if receiver and receiver[0].isupper() and len(parts) == 2:
                return CallClassificationResult(
                    call_type=CallType.CLASS_METHOD,
                    is_classmethod=True,
                    is_method=True,
                )

            return CallClassificationResult(
                call_type=CallType.METHOD,
                is_method=True,
            )

        # Lambda call heuristic
        if name.startswith("<lambda>") or name == "lambda":
            return CallClassificationResult(
                call_type=CallType.LAMBDA,
                is_lambda=True,
            )

        # Direct Function Call
        if name and name.isidentifier():
            return CallClassificationResult(
                call_type=CallType.FUNCTION,
            )

        # Fallback
        return CallClassificationResult(
            call_type=CallType.UNKNOWN,
        )

    @staticmethod
    def _is_constructor_name(name: str) -> bool:
        """
        Check if callee name follows class constructor naming convention.

        Examples:
        - 'User' -> True
        - 'FastAPI' -> True
        - 'user.login' -> False
        - 'login' -> False
        - 'fastapi.FastAPI' -> True (last component is capitalized)
        """
        if not name:
            return False
        parts = name.split(".")
        last_part = parts[-1]
        if not last_part:
            return False
        # UpperCamelCase convention: starts with uppercase letter and not ALL_CAPS constant
        return last_part[0].isupper() and not last_part.isupper()


class CallClassificationResult:
    """Helper container holding classification outcome and boolean flags."""

    def __init__(
        self,
        call_type: CallType,
        is_async: bool = False,
        is_constructor: bool = False,
        is_method: bool = False,
        is_classmethod: bool = False,
        is_staticmethod: bool = False,
        is_super_call: bool = False,
        is_lambda: bool = False,
    ) -> None:
        self.call_type = call_type
        self.is_async = is_async
        self.is_constructor = is_constructor
        self.is_method = is_method
        self.is_classmethod = is_classmethod
        self.is_staticmethod = is_staticmethod
        self.is_super_call = is_super_call
        self.is_lambda = is_lambda
