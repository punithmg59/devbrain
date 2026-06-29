import json
import logging

from anthropic import AsyncAnthropic

from app.config import get_settings
from app.schemas.impact import SimpleImpactResult, Recommendation

logger = logging.getLogger(__name__)


async def generate_recommendations(
    result: SimpleImpactResult,
) -> list[Recommendation]:
    """
    Generate 3 specific recommendations for safely changing
    the analyzed component.

    Uses Claude claude-sonnet-4-6 with a structured prompt.
    Returns empty list on any failure — recommendations are
    optional, not critical to the Impact page.

    The prompt gives Claude:
        - Component name, type, file path
        - Risk score and level
        - Blast radius number
        - List of affected APIs (up to 5)
        - List of affected services (up to 5)
        - List of affected tables (up to 5)

    Claude returns JSON array of recommendations.
    Each has: title, body, priority (high|medium|low)
    """
    try:
        settings = get_settings()

        # Build compact context — don't send the entire result
        api_names = [n.name for n in result.affected_apis[:5]]
        svc_names = [n.name for n in result.affected_services[:5]]
        tbl_names = [n.name for n in result.affected_tables[:5]]

        prompt = f"""
You are a senior software architect reviewing a proposed code change.

Component to change:
  Name: {result.node_name}
  Type: {result.node_type}
  File: {result.file_path}

Impact analysis:
  Risk level: {result.risk_score.level} ({result.risk_score.value}/10)
  Blast radius: {result.blast_radius} components affected
  APIs affected: {api_names if api_names else 'none detected'}
  Services affected: {svc_names if svc_names else 'none detected'}
  Database tables affected: {tbl_names if tbl_names else 'none detected'}

Generate exactly 3 specific, actionable recommendations for safely
making this change. Each recommendation must:
  1. Name a specific action (not generic advice like "add tests")
  2. Explain WHY it is needed based on this specific impact
  3. Be something the developer can do TODAY before making the change

Return ONLY a JSON array with no other text, no markdown, no backticks:
[
  {{"title": "short action title", "body": "specific explanation", "priority": "high"}},
  {{"title": "...", "body": "...", "priority": "medium"}},
  {{"title": "...", "body": "...", "priority": "low"}}
]
"""

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()

        # Strip markdown fences if Claude included them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)

        recommendations = []
        for item in data[:3]:
            recommendations.append(Recommendation(
                title=str(item.get("title", ""))[:200],
                body=str(item.get("body", ""))[:1000],
                priority=str(item.get("priority", "medium")),
            ))

        logger.info(
            "Generated %d recommendations for node %s",
            len(recommendations), result.node_name
        )
        return recommendations

    except Exception as exc:
        logger.warning(
            "Recommendation generation failed for %s: %s",
            result.node_name, exc
        )
        return []
