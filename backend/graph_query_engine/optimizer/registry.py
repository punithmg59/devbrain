# backend/graph_query_engine/optimizer/registry.py
"""Registry for all optimization rules.
Provides registration, lookup, enable/disable, and ordering based on dependencies
and rule priorities.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Set

from .rules import OptimizationRule
from .phase import OptimizationPhase


class OptimizationRuleRegistry:
    """Thread-safe singleton registry for optimizer rules.

    The primary configuration mechanism is the API provided by this class.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._rules: Dict[str, OptimizationRule] = {}
                cls._instance._phases: Dict[str, OptimizationPhase] = {}
            return cls._instance

    def clear(self) -> None:
        """Clears all registered rules and phases (useful for testing or reset)."""
        with self._lock:
            self._rules.clear()
            self._phases.clear()

    # ---------- rule management ----------
    def register_rule(self, rule: OptimizationRule) -> None:
        """Add a rule to the registry (overwrites an existing rule with same id)."""
        self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> OptimizationRule:
        return self._rules[rule_id]

    def enable_rule(self, rule_id: str) -> None:
        rule = self._rules[rule_id]
        if not rule.enabled:
            self._rules[rule_id] = rule.model_copy(update={"enabled": True})

    def disable_rule(self, rule_id: str) -> None:
        rule = self._rules[rule_id]
        if rule.enabled:
            self._rules[rule_id] = rule.model_copy(update={"enabled": False})

    # ---------- phase management ----------
    def register_phase(self, phase: OptimizationPhase) -> None:
        self._phases[phase.name] = phase

    def get_phase(self, name: str) -> OptimizationPhase:
        return self._phases[name]

    def get_all_phases(self) -> List[OptimizationPhase]:
        return list(self._phases.values())

    # ---------- ordering utilities ----------
    def _topological_sort_phases(self) -> List[OptimizationPhase]:
        """Return phases ordered by dependencies (DAG) with priority fallback.
        Raises ValueError if a cycle is detected.
        """
        graph: Dict[str, Set[str]] = {name: set(phase.dependencies) for name, phase in self._phases.items()}
        visited: Set[str] = set()
        temp_mark: Set[str] = set()
        result: List[OptimizationPhase] = []

        def visit(node: str):
            if node in temp_mark:
                raise ValueError(f"Cycle detected in phase dependencies involving '{node}'")
            if node not in visited:
                temp_mark.add(node)
                for dep in graph.get(node, []):
                    if dep not in self._phases:
                        raise ValueError(f"Phase '{node}' depends on unknown phase '{dep}'")
                    visit(dep)
                temp_mark.remove(node)
                visited.add(node)
                result.append(self._phases[node])

        for phase_name in self._phases:
            if phase_name not in visited:
                visit(phase_name)

        result.sort(key=lambda p: p.priority)
        return result

    def ordered_phases(self) -> List[OptimizationPhase]:
        """Public accessor returning phases ready for execution."""
        return self._topological_sort_phases()

    # ---------- rule ordering within a phase ----------
    @staticmethod
    def order_rules(rules: List[OptimizationRule]) -> List[OptimizationRule]:
        """Return rules sorted by priority (ascending)."""
        return sorted(rules, key=lambda r: r.priority)


__all__ = ["OptimizationRuleRegistry"]
