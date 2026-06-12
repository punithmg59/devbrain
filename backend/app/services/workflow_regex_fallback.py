"""Regex workflow fallback when DB workflows are not discovered yet."""

import re

WORKFLOWS = [
    {
        "id": "github_auth",
        "name": "GitHub Authentication",
        "patterns": re.compile(r"github|oauth|auth|login|callback|session", re.I),
        "user_visible": "Users may be unable to sign in or stay logged in.",
    },
    {
        "id": "repo_connect",
        "name": "Repository Connection",
        "patterns": re.compile(r"connect|repo|repository|github", re.I),
        "user_visible": "Users may fail to connect or sync GitHub repositories.",
    },
    {
        "id": "analysis",
        "name": "Code Analysis Pipeline",
        "patterns": re.compile(r"analyz|parser|graph|impact|node|edge", re.I),
        "user_visible": "Repository analysis and intelligence features may degrade.",
    },
    {
        "id": "dashboard",
        "name": "Dashboard Experience",
        "patterns": re.compile(r"dashboard|frontend|api/repos", re.I),
        "user_visible": "Dashboard data and repo cards may show errors or stale state.",
    },
    {
        "id": "api_layer",
        "name": "Public API Surface",
        "patterns": re.compile(r"api_route|router|/api/", re.I),
        "user_visible": "API clients and integrations may receive errors.",
    },
]


def apply_regex_workflow_impact(ctx) -> None:
    blob_parts = []
    if ctx.source_node:
        blob_parts.append(
            f"{ctx.source_node.get('name')} {ctx.source_node.get('file_path', '')}"
        )
    for n in ctx.impacted_nodes:
        blob_parts.append(
            f"{n.get('name')} {n.get('file_path', '')} {n.get('route_path', '')}"
        )
    blob = " ".join(blob_parts)

    workflows: list[dict] = []
    user_lines: list[str] = []
    business: list[str] = []

    for wf in WORKFLOWS:
        if wf["patterns"].search(blob):
            evidence_nodes = [
                n["name"]
                for n in ctx.impacted_nodes
                if wf["patterns"].search(
                    f"{n.get('name')} {n.get('file_path')} {n.get('route_path', '')}"
                )
            ][:5]
            workflows.append(
                {
                    "workflow_id": wf["id"],
                    "workflow_name": wf["name"],
                    "user_impact": wf["user_visible"],
                    "evidence_nodes": evidence_nodes,
                    "evidence_source": "graph_node_match",
                }
            )
            user_lines.append(wf["user_visible"])
            if ctx.scenario == "delete":
                business.append(f"{wf['name']} workflow may break entirely if removed.")
            else:
                business.append(
                    f"{wf['name']} workflow may experience errors or degraded reliability."
                )

    engineering: list[str] = []
    if ctx.apis:
        engineering.append(
            f"Regression required on {len(ctx.apis)} verified API route(s) in blast radius."
        )
    if ctx.scenario == "delete":
        engineering.insert(
            0,
            "Deletion removes a node with active incoming edges — breaking change confirmed.",
        )

    ctx.workflow_impact = workflows
    ctx.user_impact = list(dict.fromkeys(user_lines))[:6]
    ctx.business_impact = list(dict.fromkeys(business))[:6]
    ctx.engineering_impact = list(dict.fromkeys(engineering))[:8]
