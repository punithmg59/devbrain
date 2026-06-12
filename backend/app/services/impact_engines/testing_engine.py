"""Engine 5: Testing Recommendation Engine — deterministic from workflows + APIs (no LLM)."""

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2}


class TestingRecommendationEngine:
    def run(self, ctx) -> None:
        tests: list[dict] = []
        seen: set[str] = set()

        def add(title: str, priority: str, reason: str, evidence: str) -> None:
            key = title.lower()
            if key in seen:
                return
            seen.add(key)
            tests.append(
                {
                    "title": title,
                    "priority": priority,
                    "reason": reason,
                    "evidence": evidence,
                }
            )

        for wf in ctx.workflow_impact:
            pri = "critical" if ctx.risk_score_100 >= 61 else "high"
            add(
                f"End-to-end: {wf['workflow_name']}",
                pri,
                wf["user_impact"],
                f"workflow_engine:{wf['workflow_id']}",
            )

        for api in ctx.apis:
            add(
                f"{api['method']} {api['path']}",
                "critical" if ctx.risk_score_100 >= 61 else "high",
                api["inclusion_reason"],
                f"graph:api_route:{api['node_id']}",
            )

        if ctx.scenario == "delete":
            add(
                "Verify no remaining references compile/import",
                "critical",
                "Delete scenario — upstream dependents on graph",
                "change_simulator:delete",
            )

        src = ctx.source_node or {}
        if src.get("name"):
            add(
                f"Unit tests for {src['name']}",
                "high",
                "Direct change target",
                f"source_node:{src.get('id')}",
            )

        if not tests:
            add(
                "Smoke test primary application path",
                "medium",
                "Isolated or low blast radius",
                "graph:empty_blast",
            )

        tests.sort(key=lambda t: PRIORITY_ORDER.get(t["priority"], 9))
        ctx.recommended_tests = tests[:12]
