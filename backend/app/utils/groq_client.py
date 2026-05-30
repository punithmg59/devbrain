"""Groq LLM client for generating AI code summaries."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from groq import AsyncGroq

from app.config import get_settings

if TYPE_CHECKING:
    from app.models.node import Node

logger = logging.getLogger(__name__)

_client: AsyncGroq | None = None

MODEL = "llama-3.1-8b-instant"


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


async def generate_node_summary(
    node: "Node",
    repo_name: str,
) -> tuple[str, list[str]]:
    """Generate a one-line summary and tags for a code node.

    Returns:
        (summary, tags) — on *any* error returns
        ("Summary not available", []).
    """
    try:
        client = _get_client()

        code_snippet = (node.raw_code[:1500] if node.raw_code else "not available")

        prompt = (
            f"You are analyzing code for a project called {repo_name}.\n\n"
            f"Analyze this {node.node_type} named '{node.name}':\n\n"
            f"File: {node.full_path}\n"
            f"Signature: {node.signature or 'unknown'}\n"
            f"Code:\n{code_snippet}\n\n"
            "Respond in this exact JSON format only, "
            "no markdown, no explanation:\n"
            '{"summary": "One sentence describing what this code does", '
            '"tags": ["tag1", "tag2", "tag3"]}\n\n'
            "Tags should be 2-5 relevant technical keywords like: "
            "authentication, database, validation, payment, async, crud, etc."
        )

        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1,
        )

        raw = response.choices[0].message.content or ""
        # Strip possible markdown code fences
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
        raw = raw.strip()

        data = json.loads(raw)
        summary = str(data.get("summary", "Summary not available"))
        tags = [str(t) for t in data.get("tags", [])]
        return summary, tags

    except json.JSONDecodeError:
        logger.warning("Groq returned non-JSON for node %s", node.name)
        return "Summary not available", []
    except Exception:
        logger.exception("Groq summary failed for node %s", node.name)
        return "Summary not available", []
