"""Build hierarchical evidence trees from deterministic evidence chains."""

from __future__ import annotations


class EvidenceTreeService:
    def build_tree(self, chains: list[dict], source_label: str | None = None) -> list[dict]:
        if not chains:
            return []

        root_label = source_label or "repository"
        root = {
            "label": root_label,
            "node_type": "source",
            "confidence": 100.0,
            "summary": "Evidence root",
            "children": [],
        }

        for chain in chains:
            parent = root
            for step in chain.get("steps", []):
                child = next(
                    (
                        c
                        for c in parent["children"]
                        if c["label"] == step["label"] and c["node_type"] == step["step_type"]
                    ),
                    None,
                )
                if not child:
                    child = {
                        "label": step["label"],
                        "node_type": step["step_type"],
                        "confidence": float(chain.get("confidence_percent", 0)),
                        "summary": chain.get("summary", ""),
                        "children": [],
                    }
                    parent["children"].append(child)
                parent = child

        return [root]
