"""
Graph Query Engine Internal Package.

PRIVATE IMPLEMENTATION DETAILS ONLY.
This package and all sub-packages (planner, traversal, pipeline, cache, optimization, validation)
contain internal engine implementation logic.

DEPENDENCY RULE:
- Code inside `graph_query_engine.internal.*` MUST NEVER be imported by downstream modules
  or external components outside `graph_query_engine`.
"""

__all__: list[str] = []
