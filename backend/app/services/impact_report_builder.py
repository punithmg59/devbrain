import asyncio
import json
import logging
import re
from typing import Any

from app.schemas.impact import (
    AffectedAPI,
    DeploymentAdvice,
    GraphEdge,
    GraphNode,
    ImpactGraph,
    ResolvedEntity,
    TestRecommendation,
)
from app.services.impact_risk_engine import ImpactRiskEngine, legacy_level_from_score_100

logger = logging.getLogger(__name__)

risk_engine = ImpactRiskEngine()


class ImpactReportBuilder:
    def build_graph(
        self,
        source_node: dict,
        impacted_nodes: list[dict],
    ) -> ImpactGraph:
        graph_nodes: list[GraphNode] = [
            GraphNode(
                id=str(source_node["id"]),
                name=source_node["name"],
                node_type=source_node.get("node_type", "unknown"),
                file_path=source_node.get("file_path") or "",
                risk_tier="medium",
                is_source=True,
                depth=0,
            )
        ]
        seen = {str(source_node["id"])}
        for n in impacted_nodes[:80]:
            nid = str(n["id"])
            if nid in seen:
                continue
            seen.add(nid)
            graph_nodes.append(
                GraphNode(
                    id=nid,
                    name=n["name"],
                    node_type=n.get("node_type", "unknown"),
                    file_path=n.get("file_path") or "",
                    risk_tier=n.get("risk_tier", "low"),
                    is_source=False,
                    depth=n.get("depth", 1),
                )
            )
        return ImpactGraph(nodes=graph_nodes, edges=[])

    def attach_inclusion_reasons(
        self,
        source_node: dict,
        nodes: list[dict],
    ) -> list[dict]:
        for n in nodes:
            direction = n.get("direction", "downstream")
            edge = n.get("edge_type") or "relates"
            depth = n.get("depth", 1)
            n["inclusion_reason"] = (
                f"Graph trace: {direction} from '{source_node['name']}' "
                f"at depth {depth} via '{edge}' — verified edge in repository graph"
            )
            if n.get("node_type") == "api_route" and n.get("route_path"):
                n["inclusion_reason"] += f" (route {n.get('http_method', 'GET')} {n['route_path']})"
        return nodes

    def rule_based_report(
        self,
        query: str,
        source_node: dict,
        impacted_nodes: list[dict],
        score_100: int,
        tier: str,
        systems: list[str],
        apis: list[dict],
    ) -> dict[str, Any]:
        tier_label = tier.upper()
        api_lines = [
            f"{a['method']} {a['path']}" for a in apis[:6]
        ]
        fn_names = [n["name"] for n in impacted_nodes[:8] if n.get("node_type") != "api_route"]

        business = []
        if any(s in systems for s in ("Authentication", "GitHub Integration")):
            business.append("User sign-in and GitHub authorization flows may be disrupted.")
            business.append("Repository connection from the dashboard could fail.")
        if "Repository Management" in systems:
            business.append("Repository onboarding and sync workflows may break.")
        if "Analysis Pipeline" in systems:
            business.append("Code analysis jobs may fail or produce incomplete results.")
        if not business:
            business.append("Internal application behavior may change for dependent modules.")
            if fn_names:
                business.append(f"Features relying on {fn_names[0]} and related code paths may regress.")

        developer = []
        if apis:
            developer.append(f"Review and regression-test API handlers: {', '.join(api_lines[:3])}.")
        if fn_names:
            developer.append(
                f"Validate call chains through: {', '.join(fn_names[:5])}."
            )
        developer.append("Run targeted unit and integration tests before merging.")

        tests = self._default_tests(systems, apis, tier)
        deploy = self._default_deployment(tier, systems)

        executive = (
            f"Changing '{source_node['name']}' carries {tier_label} risk ({score_100}/100). "
            f"{len(impacted_nodes)} graph-connected components across "
            f"{len({n.get('file_path') for n in impacted_nodes})} files are in the blast radius."
        )

        return {
            "executive_summary": executive,
            "business_impact": business[:5],
            "developer_impact": developer[:5],
            "risk_analysis": (
                f"Risk score {score_100}/100 driven by {len(apis)} API(s), "
                f"{len(impacted_nodes)} connected nodes, and exposure in: "
                f"{', '.join(systems)}."
            ),
            "ai_recommendation": (
                f"Treat this as a {tier_label} change. Prioritize end-to-end tests on "
                f"{systems[0] if systems else 'core flows'} before production deploy."
            ),
            "recommended_tests": tests,
            "deployment_advice": deploy,
            "pr_checklist": self._pr_checklist(systems, apis),
            "qa_checklist": self._qa_checklist(systems, apis),
            "rollback_plan": deploy.get("rollback_items", []),
            "rollback_items": deploy.get("rollback_items", []),
        }

    def _default_tests(
        self, systems: list[str], apis: list[dict], tier: str
    ) -> list[dict]:
        tests: list[dict] = []
        priority = "critical" if tier in ("critical", "high") else "high"

        if "Authentication" in systems or "GitHub Integration" in systems:
            tests.append(
                {
                    "title": "Login via GitHub OAuth",
                    "priority": "critical",
                    "reason": "Auth-related nodes in impact graph",
                }
            )
            tests.append(
                {
                    "title": "Session persistence after page refresh",
                    "priority": priority,
                    "reason": "Session management may be affected",
                }
            )
        if "Repository Management" in systems:
            tests.append(
                {
                    "title": "Connect a GitHub repository from dashboard",
                    "priority": "critical",
                    "reason": "Repo connect flow in blast radius",
                }
            )
            tests.append(
                {
                    "title": "Trigger repository analysis",
                    "priority": "high",
                    "reason": "Analysis pipeline dependency",
                }
            )
        for api in apis[:3]:
            tests.append(
                {
                    "title": f"Exercise {api['method']} {api['path']}",
                    "priority": "high",
                    "reason": api["inclusion_reason"],
                }
            )
        if not tests:
            tests.append(
                {
                    "title": "Run smoke test on primary user workflow",
                    "priority": "medium",
                    "reason": "Baseline validation for isolated change",
                }
            )
        return tests[:8]

    def _default_deployment(self, tier: str, systems: list[str]) -> dict:
        recs = ["Deploy behind a feature flag when possible."]
        monitoring = ["Error rate on affected API routes", "Application error logs"]
        rollback = "Rollback if error rate exceeds 2% for 10 minutes."

        if tier in ("critical", "high"):
            recs.append("Use canary or staged rollout.")
            recs.append("Avoid Friday/holiday deploys.")
        if "Authentication" in systems:
            monitoring.append("OAuth callback success rate")
            monitoring.append("Login success rate")
        if "GitHub Integration" in systems:
            monitoring.append("GitHub API error rate")

        return {
            "summary": "Safe deployment requires staged rollout and close monitoring.",
            "recommendations": recs,
            "monitoring": monitoring,
            "rollback_trigger": rollback,
            "rollback_items": [
                "Revert commit and redeploy previous release",
                "Clear Redis/session cache if auth state corrupted",
                "Verify GitHub OAuth redirect URLs unchanged",
            ],
        }

    def _pr_checklist(self, systems: list[str], apis: list[dict]) -> list[str]:
        items = [
            "Impact Radar report attached or linked in PR description",
            "All critical/high tests from impact report executed",
        ]
        if apis:
            items.append("API contract changes documented")
        if "Authentication" in systems:
            items.append("Auth flow manually verified in staging")
        return items

    def _qa_checklist(self, systems: list[str], apis: list[dict]) -> list[str]:
        items = ["Regression pass on dashboard happy path"]
        for api in apis[:5]:
            items.append(f"QA: {api['method']} {api['path']} — expected status codes")
        return items[:8]

    async def generate_ai_report(
        self,
        query: str,
        source_node: dict,
        impacted_nodes: list[dict],
        score_100: int,
        tier: str,
        systems: list[str],
        apis: list[dict],
        repo_name: str = "repository",
    ) -> dict[str, Any] | None:
        verified_nodes = [
            {
                "name": n["name"],
                "type": n.get("node_type"),
                "file": n.get("file_path"),
                "depth": n.get("depth"),
                "reason": n.get("inclusion_reason", ""),
            }
            for n in impacted_nodes[:15]
        ]
        verified_apis = [
            {"method": a["method"], "path": a["path"], "reason": a["inclusion_reason"]}
            for a in apis[:8]
        ]

        prompt = f"""You are a Staff Engineer writing an impact report for {repo_name}.
The user asked: "{query}"

ONLY use facts from VERIFIED_GRAPH below. Do NOT invent files, APIs, or components.

SOURCE (change target):
{json.dumps({"name": source_node["name"], "type": source_node.get("node_type"), "file": source_node.get("file_path")})}

VERIFIED_GRAPH nodes (max 15):
{json.dumps(verified_nodes)}

VERIFIED APIs:
{json.dumps(verified_apis)}

SYSTEMS: {json.dumps(systems)}
RISK: {score_100}/100 ({tier})

Respond with ONLY valid JSON (no markdown):
{{
  "executive_summary": "2 sentences, workflow-focused, no bullet list of node names",
  "business_impact": ["user-facing consequence 1", "..."],
  "developer_impact": ["engineering task 1", "..."],
  "risk_analysis": "why this score, reference real systems",
  "ai_recommendation": "staff engineer advice, no repeating the node list",
  "recommended_tests": [{{"title": "...", "priority": "critical|high|medium", "reason": "..."}}],
  "deployment_advice": {{
    "summary": "...",
    "recommendations": ["..."],
    "monitoring": ["..."],
    "rollback_trigger": "..."
  }},
  "pr_checklist": ["..."],
  "qa_checklist": ["..."]
}}

Rules:
- Do NOT list every function name in executive_summary
- Focus on workflows: login, repo connect, analysis, APIs
- Every test must map to a verified system or API
- Max 5 items per array"""

        try:
            from app.utils.groq_client import groq_client

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=900,
                    temperature=0.15,
                ),
            )
            text = response.choices[0].message.content.strip()
            return self._parse_json(text)
        except Exception as e:
            logger.warning("Groq V2 report failed: %s", e)
            return None

    def _parse_json(self, text: str) -> dict[str, Any] | None:
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    return None
        return None

    def merge_reports(
        self,
        rule: dict[str, Any],
        ai: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not ai:
            return rule
        merged = {**rule}
        for key in (
            "executive_summary",
            "business_impact",
            "developer_impact",
            "risk_analysis",
            "ai_recommendation",
        ):
            if ai.get(key):
                merged[key] = ai[key]
        if ai.get("recommended_tests"):
            merged["recommended_tests"] = ai["recommended_tests"][:8]
        if ai.get("deployment_advice"):
            merged["deployment_advice"] = {
                **rule.get("deployment_advice", {}),
                **ai["deployment_advice"],
            }
        for key in ("pr_checklist", "qa_checklist"):
            if ai.get(key):
                merged[key] = ai[key][:8]
        return merged

    def to_schema_objects(self, report: dict[str, Any], apis: list[dict]) -> dict:
        tests = [
            TestRecommendation(
                title=t.get("title", "Test"),
                priority=t.get("priority", "medium"),
                reason=t.get("reason", "Impact graph coverage"),
            )
            for t in report.get("recommended_tests", [])
            if t.get("title")
        ]
        deploy_raw = report.get("deployment_advice") or {}
        deploy = DeploymentAdvice(
            summary=deploy_raw.get("summary", "Review before deploy."),
            recommendations=deploy_raw.get("recommendations", [])[:6],
            monitoring=deploy_raw.get("monitoring", [])[:6],
            rollback_trigger=deploy_raw.get("rollback_trigger"),
        )
        affected_apis = [
            AffectedAPI(
                method=a["method"],
                path=a["path"],
                node_id=a["node_id"],
                name=a["name"],
                file_path=a["file_path"],
                inclusion_reason=a["inclusion_reason"],
            )
            for a in apis
        ]
        return {
            "executive_summary": report.get("executive_summary", ""),
            "business_impact": report.get("business_impact", [])[:6],
            "developer_impact": report.get("developer_impact", [])[:6],
            "risk_analysis": report.get("risk_analysis", ""),
            "ai_recommendation": report.get("ai_recommendation", ""),
            "recommended_tests": tests,
            "deployment_advice": deploy,
            "pr_checklist": report.get("pr_checklist", [])[:8],
            "qa_checklist": report.get("qa_checklist", [])[:8],
            "rollback_plan": report.get("rollback_plan", deploy_raw.get("rollback_items", []))[:6],
            "affected_apis": affected_apis,
        }
