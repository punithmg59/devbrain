"""Engine 6: Deployment Safety Engine — rollout, rollback, monitoring (no LLM)."""

class DeploymentSafetyEngine:
    def run(self, ctx) -> None:
        tier = ctx.risk_breakdown.get("tier", "low")
        score = ctx.risk_score_100

        rollout = {
            "strategy": self._rollout_strategy(score, ctx.scenario),
            "steps": self._rollout_steps(score, ctx),
            "feature_flag_recommended": score >= 41,
            "canary_recommended": score >= 61,
            "evidence": f"risk_score={score}, scenario={ctx.scenario}",
        }

        rollback = {
            "strategy": "immediate_revert" if score >= 61 else "standard_revert",
            "steps": [
                "Revert deployment to previous known-good release",
                "Invalidate Redis/session caches if auth touched",
                "Re-run health checks on affected API routes",
            ],
            "trigger": self._rollback_trigger(score),
            "evidence": "deployment_safety_engine",
        }

        monitoring = self._monitoring(ctx)

        ctx.rollout_strategy = rollout
        ctx.rollback_strategy = rollback
        ctx.monitoring_plan = monitoring

    def _rollout_strategy(self, score: int, scenario: str) -> str:
        if scenario == "delete":
            return "blocked"
        if score >= 81:
            return "staged_canary_with_approval"
        if score >= 61:
            return "canary_10_percent"
        if score >= 41:
            return "staged_rollout"
        return "standard_deploy"

    def _rollout_steps(self, score: int, ctx) -> list[str]:
        steps = []
        if score >= 41:
            steps.append("Enable behind feature flag")
        if score >= 61:
            steps.extend(
                [
                    "Deploy to 10% traffic",
                    "Monitor error budgets for 30 minutes",
                    "Expand to 50% then 100%",
                ]
            )
        else:
            steps.append("Deploy to staging, run recommended tests, promote to production")
        if any("auth" in s.lower() or "github" in s.lower() for s in ctx.services):
            steps.append("Verify OAuth redirect URLs in staging before prod")
        return steps

    def _rollback_trigger(self, score: int) -> str:
        if score >= 61:
            return "Rollback if error rate > 2% for 10 min or login success drops > 5%"
        return "Rollback if new critical errors appear in affected modules"

    def _monitoring(self, ctx) -> list[str]:
        items = ["Application error rate", "P95 latency on affected routes"]
        for api in ctx.apis[:5]:
            items.append(f"{api['method']} {api['path']} — 5xx rate")
        if any("Authentication" in s for s in ctx.services):
            items.extend(["OAuth callback success rate", "Login completion rate"])
        if any("Database" in s or "Caching" in s for s in ctx.services):
            items.append("Database connection pool / Redis errors")
        return items[:10]
