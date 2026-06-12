import re
from typing import Any

AUTH_PATTERNS = re.compile(
    r"auth|oauth|login|session|token|password|credential|jwt|cookie|github",
    re.I,
)
DB_PATTERNS = re.compile(
    r"database|db_|postgres|sqlalchemy|redis|migrate|repository|query",
    re.I,
)
CRITICAL_PATH_PATTERNS = re.compile(
    r"main\.py|app\.py|router|middleware|config|settings|connect|analyze",
    re.I,
)

SYSTEM_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"auth|oauth|login|session", re.I), "Authentication"),
    (re.compile(r"github|oauth|connect", re.I), "GitHub Integration"),
    (re.compile(r"repo|repository", re.I), "Repository Management"),
    (re.compile(r"redis|cache", re.I), "Caching"),
    (re.compile(r"database|db|sql|postgres", re.I), "Database"),
    (re.compile(r"api|router|route", re.I), "API Layer"),
    (re.compile(r"analysis|parser|graph", re.I), "Analysis Pipeline"),
    (re.compile(r"middleware", re.I), "Middleware"),
    (re.compile(r"dashboard|frontend", re.I), "Dashboard"),
]


def risk_tier_from_score(score_100: int) -> str:
    if score_100 <= 20:
        return "safe"
    if score_100 <= 40:
        return "low"
    if score_100 <= 60:
        return "medium"
    if score_100 <= 80:
        return "high"
    return "critical"


def legacy_level_from_score_100(score_100: int) -> str:
    tier = risk_tier_from_score(score_100)
    if tier == "safe":
        return "low"
    return tier


class ImpactRiskEngine:
    def score_node(self, node: dict, max_depth: int) -> dict:
        """Per-node dynamic score 0-1 for sorting and graph colors."""
        depth = node.get("depth", 1)
        depth_factor = max(0.2, 1.0 - (depth / max(max_depth, 1)) * 0.5)
        type_weight = {
            "api_route": 1.0,
            "class": 0.75,
            "method": 0.65,
            "function": 0.55,
        }.get(node.get("node_type", ""), 0.45)

        text_blob = " ".join(
            filter(
                None,
                [
                    node.get("name", ""),
                    node.get("file_path", ""),
                    node.get("route_path", ""),
                ],
            )
        )
        critical_bonus = 0.15 if CRITICAL_PATH_PATTERNS.search(text_blob) else 0
        auth_bonus = 0.12 if AUTH_PATTERNS.search(text_blob) else 0
        db_bonus = 0.08 if DB_PATTERNS.search(text_blob) else 0

        raw = min(1.0, (type_weight + critical_bonus + auth_bonus + db_bonus) * depth_factor)
        node["risk_score"] = round(raw, 3)
        node["risk_tier"] = risk_tier_from_score(int(raw * 100))
        return node

    def calculate_overall(
        self,
        impacted_nodes: list[dict],
        source_node: dict | None,
        max_depth: int,
        resolution_confidence: float,
    ) -> tuple[int, str, float]:
        api_count = sum(1 for n in impacted_nodes if n.get("node_type") == "api_route")
        fn_count = sum(
            1
            for n in impacted_nodes
            if n.get("node_type") in ("function", "method", "class")
        )
        file_count = len({n.get("file_path") for n in impacted_nodes if n.get("file_path")})
        max_d = max((n.get("depth", 0) for n in impacted_nodes), default=0)

        all_text = " ".join(
            (source_node or {}).get("name", "")
            + " "
            + " ".join(
                f"{n.get('name','')} {n.get('file_path','')}" for n in impacted_nodes[:30]
            )
        )
        auth_weight = 0.4 if AUTH_PATTERNS.search(all_text) else 0.0
        db_weight = 0.25 if DB_PATTERNS.search(all_text) else 0.0
        critical_weight = 0.35 if CRITICAL_PATH_PATTERNS.search(all_text) else 0.0

        depth_component = min(20, max_d * 4)
        api_component = min(30, api_count * 10)
        fn_component = min(20, fn_count * 2)
        file_component = min(15, file_count * 3)

        score_100 = int(
            min(
                100,
                api_component * 0.3
                + fn_component * 0.2
                + depth_component * 0.1
                + (auth_weight + db_weight + critical_weight) * 100 * 0.4,
            )
        )
        if api_count >= 3:
            score_100 = min(100, score_100 + 10)
        if fn_count == 0 and api_count == 0:
            score_100 = min(score_100, 25)

        tier = risk_tier_from_score(score_100)
        confidence = round(
            min(
                0.98,
                0.55
                + resolution_confidence * 0.25
                + min(0.2, len(impacted_nodes) * 0.02),
            ),
            2,
        )
        legacy_score = score_100 / 100.0
        return score_100, tier, confidence if impacted_nodes else resolution_confidence

    def infer_systems(self, nodes: list[dict], source: dict | None) -> list[str]:
        systems: list[str] = []
        blob_parts = [source.get("name", "") if source else ""]
        blob_parts += [f"{n.get('name','')} {n.get('file_path','')}" for n in nodes]
        blob = " ".join(blob_parts)
        for pattern, label in SYSTEM_RULES:
            if pattern.search(blob) and label not in systems:
                systems.append(label)
        return systems[:8] or ["Application Core"]

    def extract_apis(self, nodes: list[dict]) -> list[dict]:
        apis = []
        for n in nodes:
            if n.get("node_type") != "api_route":
                continue
            method = (n.get("http_method") or "GET").upper()
            path = n.get("route_path") or n.get("name", "")
            apis.append(
                {
                    "method": method,
                    "path": path,
                    "node_id": str(n["id"]),
                    "name": n["name"],
                    "file_path": n.get("file_path") or "",
                    "inclusion_reason": (
                        f"API route reachable from change at depth {n.get('depth', 0)} "
                        f"via graph edge '{n.get('edge_type', 'calls')}'"
                    ),
                }
            )
        return apis
