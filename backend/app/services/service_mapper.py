"""Map discovered workflows to engineering services — deterministic catalog."""

from __future__ import annotations

WORKFLOW_SERVICE_MAP: dict[str, str] = {
    "GitHub Authentication": "Auth Service",
    "Session Management": "Auth Service",
    "Repository Connection": "Repository Service",
    "Repository Analysis": "Analysis Service",
    "Code Analysis Pipeline": "Analysis Service",
    "Impact Radar": "Intelligence Service",
    "Dashboard Experience": "Frontend Service",
    "Public API Surface": "API Gateway",
}

WORKFLOW_TYPE_DEFAULTS: dict[str, str] = {
    "GitHub Authentication": "authentication",
    "Session Management": "session",
    "Repository Connection": "integration",
    "Repository Analysis": "analysis",
    "Code Analysis Pipeline": "analysis",
    "Impact Radar": "intelligence",
    "Dashboard Experience": "frontend",
    "Public API Surface": "api",
}


def map_workflow_to_service(workflow_name: str) -> str:
    if workflow_name in WORKFLOW_SERVICE_MAP:
        return WORKFLOW_SERVICE_MAP[workflow_name]
    lower = workflow_name.lower()
    if any(k in lower for k in ("auth", "oauth", "login", "session")):
        return "Auth Service"
    if any(k in lower for k in ("repo", "repository", "connect")):
        return "Repository Service"
    if any(k in lower for k in ("analyz", "parser", "graph")):
        return "Analysis Service"
    if "api" in lower or "route" in lower:
        return "API Gateway"
    return "Core Service"


def infer_workflow_type(workflow_name: str) -> str:
    return WORKFLOW_TYPE_DEFAULTS.get(workflow_name, "general")
