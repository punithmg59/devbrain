"""
analysis/scope_resolution/__init__.py
--------------------------------------
Phase 4.5 — Scope Resolution & Lexical Visibility Package.

Exports the core scope data structures, stack manager, lexical scope builder,
scope resolution coordinator, and scope integrity validator.
"""

from analysis.scope_resolution.scope_builder import ScopeBuilder
from analysis.scope_resolution.scope_resolver import ScopeResolver
from analysis.scope_resolution.scope_stack import ScopeStack
from analysis.scope_resolution.scope_tree import ScopeTree
from analysis.scope_resolution.scope_validator import ScopeValidator

__all__ = [
    "ScopeTree",
    "ScopeStack",
    "ScopeBuilder",
    "ScopeResolver",
    "ScopeValidator",
]
