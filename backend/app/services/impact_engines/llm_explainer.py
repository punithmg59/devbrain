"""LLM Explainer — narrative only; never discovers dependencies."""

import asyncio
import json
import logging
import re

logger = logging.getLogger(__name__)


class LLMExplainerEngine:
    async def run(self, ctx) -> None:
        ctx.executive_summary = self._deterministic_executive(ctx)
        ctx.why_this_matters = self._deterministic_why(ctx)
        ctx.staff_engineer_recommendation = self._deterministic_staff(ctx)

        ai = await self._narrative(ctx)
        if ai:
            if ai.get("executive_summary"):
                ctx.executive_summary = ai["executive_summary"]
            if ai.get("why_this_matters"):
                ctx.why_this_matters = ai["why_this_matters"]
            if ai.get("staff_engineer_recommendation"):
                ctx.staff_engineer_recommendation = ai["staff_engineer_recommendation"]

    def _deterministic_executive(self, ctx) -> str:
        src = ctx.source_node or {}
        br = ctx.blast_radius
        return (
            f"{scenario_phrase(ctx)} '{src.get('name', ctx.query)}' "
            f"{'is not recommended' if not ctx.should_proceed else 'can proceed with controls'}. "
            f"Verified blast radius: {br.get('total_nodes', 0)} nodes, "
            f"{br.get('api_routes', 0)} APIs, risk {ctx.risk_score_100}/100. "
            f"{ctx.proceed_label}"
        )

    def _deterministic_why(self, ctx) -> str:
        if ctx.workflow_impact:
            names = ", ".join(w["workflow_name"] for w in ctx.workflow_impact[:3])
            return (
                f"This change sits on the critical path for: {names}. "
                f"Graph evidence links {ctx.blast_radius.get('verified_edges', 0)} "
                f"edges to production workflows."
            )
        return (
            "Impact is contained to a small verified subgraph. "
            "Standard review is sufficient."
        )

    def _deterministic_staff(self, ctx) -> str:
        return (
            f"Decision: {ctx.change_recommendation.upper().replace('_', ' ')}. "
            f"{ctx.proceed_label} "
            f"Run {len(ctx.recommended_tests)} recommended tests. "
            f"Rollout: {ctx.rollout_strategy.get('strategy', 'standard')}."
        )

    async def _narrative(self, ctx) -> dict | None:
        facts = {
            "query": ctx.query,
            "scenario": ctx.scenario,
            "should_proceed": ctx.should_proceed,
            "risk_score": ctx.risk_score_100,
            "change_recommendation": ctx.change_recommendation,
            "workflows": [w["workflow_name"] for w in ctx.workflow_impact],
            "user_impact": ctx.user_impact[:4],
            "apis": [f"{a['method']} {a['path']}" for a in ctx.apis[:5]],
            "blast_radius": ctx.blast_radius,
            "risk_breakdown_total": ctx.risk_breakdown.get("total"),
        }
        prompt = f"""You are Staff Engineer + Architect. Write narrative ONLY from FACTS.
Do NOT add components not in FACTS. Do NOT list every function name.

FACTS: {json.dumps(facts)}

Return JSON only:
{{
  "executive_summary": "2 sentences: should they make this change?",
  "why_this_matters": "2 sentences: business/workflow why",
  "staff_engineer_recommendation": "2-3 sentences: concrete advice"
}}"""

        try:
            from app.utils.groq_client import groq_client

            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=400,
                    temperature=0.1,
                ),
            )
            text = resp.choices[0].message.content.strip()
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\n?", "", text)
                text = re.sub(r"\n?```$", "", text)
            return json.loads(text)
        except Exception as e:
            logger.warning("LLM explainer skipped: %s", e)
            return None


def scenario_phrase(ctx) -> str:
    labels = {"modify": "Modifying", "delete": "Deleting", "refactor": "Refactoring"}
    return labels.get(ctx.scenario, "Changing")
