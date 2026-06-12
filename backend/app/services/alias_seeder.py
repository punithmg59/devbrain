"""Seed aliases after repository analysis — deterministic, no LLM."""

import logging
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alias import Alias
from app.models.node import Node

logger = logging.getLogger(__name__)

# node_name (lowercase) -> list of human aliases
NODE_ALIAS_CATALOG: dict[str, list[str]] = {
    "github_callback": [
        "GitHub Login",
        "GitHub OAuth",
        "GitHub Authentication",
        "OAuth Callback",
        "User Sign In",
        "GitHub Sign In",
    ],
    "save_github_token": [
        "Save GitHub Token",
        "GitHub Token Storage",
        "OAuth Token Handler",
    ],
    "create_session_token": [
        "Session Management",
        "Create Session",
        "User Session",
        "Session Token",
    ],
    "connect_repo": [
        "Repository Connection",
        "Connect GitHub Repo",
        "Add Repository",
        "Repository Onboarding",
        "Connect Repository",
    ],
    "analyze_repo": [
        "Repository Analysis",
        "Code Analysis",
        "Repo Scan",
        "Repository Parsing",
        "Analyze Repository",
    ],
    "run_repo_analysis": [
        "Run Analysis",
        "Start Analysis",
        "Analysis Pipeline",
    ],
    "get_current_user": [
        "Current User",
        "Auth Middleware",
        "Get User Session",
    ],
    "login": [
        "Login",
        "User Login",
        "Sign In",
    ],
    "logout": [
        "Logout",
        "Sign Out",
    ],
}

WORKFLOW_ALIASES: dict[str, list[str]] = {
    "GitHub Authentication": [
        "GitHub Login",
        "GitHub OAuth",
        "OAuth Flow",
        "GitHub Sign In",
        "What breaks if I change GitHub login",
    ],
    "Repository Connection": [
        "Connect Repo",
        "Repository Onboarding",
        "Add GitHub Repository",
    ],
    "Repository Analysis": [
        "Code Analysis",
        "Repo Analysis",
        "Analyze Codebase",
        "Repository Parsing",
    ],
    "Session Management": [
        "User Session",
        "Session Token",
        "Auth Session",
    ],
}

POPULAR_SEARCHES = [
    "GitHub Login",
    "Repository Connection",
    "Code Analysis",
    "Session Management",
    "OAuth",
    "Repository Onboarding",
]


async def seed_aliases_for_repo(repo_id: UUID, db: AsyncSession) -> int:
    """Insert aliases for all nodes in repo. Returns count inserted."""
    await db.execute(delete(Alias).where(Alias.repo_id == repo_id))

    result = await db.execute(select(Node).where(Node.repo_id == repo_id))
    nodes = result.scalars().all()
    count = 0

    for node in nodes:
        key = node.name.lower()
        catalog = NODE_ALIAS_CATALOG.get(key, [])
        for alias_text in catalog:
            db.add(
                Alias(
                    repo_id=repo_id,
                    node_id=node.id,
                    file_id=node.file_id,
                    entity_type=node.node_type,
                    alias=alias_text,
                    weight=1.0,
                )
            )
            count += 1

        humanized = _humanize_name(node.name)
        if humanized and humanized.lower() != node.name.lower():
            db.add(
                Alias(
                    repo_id=repo_id,
                    node_id=node.id,
                    file_id=node.file_id,
                    entity_type=node.node_type,
                    alias=humanized,
                    weight=0.8,
                )
            )
            count += 1

    for workflow_name, aliases in WORKFLOW_ALIASES.items():
        db.add(
            Alias(
                repo_id=repo_id,
                node_id=None,
                file_id=None,
                entity_type="workflow",
                alias=workflow_name,
                weight=1.2,
            )
        )
        count += 1
        for alias_text in aliases:
            db.add(
                Alias(
                    repo_id=repo_id,
                    node_id=None,
                    file_id=None,
                    entity_type="workflow",
                    alias=alias_text,
                    weight=1.0,
                )
            )
            count += 1

    await db.flush()
    logger.info("Seeded %d aliases for repo %s", count, repo_id)
    return count


async def link_workflow_aliases_to_nodes(repo_id: UUID, db: AsyncSession) -> None:
    """Attach workflow alias hints to matching nodes by name patterns."""
    workflow_node_map = {
        "GitHub Authentication": ["github", "oauth", "callback", "token", "auth"],
        "Repository Connection": ["connect", "repo"],
        "Repository Analysis": ["analyz", "parser", "collect"],
        "Session Management": ["session", "token"],
    }
    result = await db.execute(select(Node).where(Node.repo_id == repo_id))
    nodes = result.scalars().all()

    for wf_name, patterns in workflow_node_map.items():
        for node in nodes:
            blob = f"{node.name} {node.full_path}".lower()
            if any(p in blob for p in patterns):
                db.add(
                    Alias(
                        repo_id=repo_id,
                        node_id=node.id,
                        file_id=node.file_id,
                        entity_type="workflow_link",
                        alias=wf_name,
                        weight=1.1,
                    )
                )
    await db.flush()


def _humanize_name(name: str) -> str:
    if "_" not in name and name.islower():
        return name
    return " ".join(part.capitalize() for part in name.replace(".", "_").split("_") if part)


async def index_node_embeddings(repo_id: UUID, db: AsyncSession) -> int:
    """Deterministic bag-of-words embeddings for semantic search (no LLM)."""
    from app.services.resolver_service import build_deterministic_embedding

    result = await db.execute(
        text("""
            SELECT n.id, n.name, n.node_type, n.full_path, n.summary,
                   COALESCE(rf.file_path, '') as file_path
            FROM nodes n
            LEFT JOIN repo_files rf ON n.file_id = rf.id
            WHERE n.repo_id = :repo_id
        """),
        {"repo_id": str(repo_id)},
    )
    rows = result.mappings().all()
    count = 0
    for row in rows:
        source = " ".join(
            filter(
                None,
                [row["name"], row["node_type"], row["file_path"], row["summary"] or ""],
            )
        )
        emb = build_deterministic_embedding(source)
        await db.execute(
            text("""
                INSERT INTO node_embeddings (repo_id, node_id, embedding, source_text, updated_at)
                VALUES (:repo_id, :node_id, :embedding::jsonb, :source_text, now())
                ON CONFLICT (repo_id, node_id)
                DO UPDATE SET embedding = EXCLUDED.embedding,
                              source_text = EXCLUDED.source_text,
                              updated_at = now()
            """),
            {
                "repo_id": str(repo_id),
                "node_id": str(row["id"]),
                "embedding": emb,
                "source_text": source[:2000],
            },
        )
        count += 1
    await db.flush()
    return count
