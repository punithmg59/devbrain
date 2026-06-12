"""Evidence chain generation and summarization."""

from __future__ import annotations

from typing import Iterable


class EvidenceExplainer:
    def build_chain(
        self,
        source_name: str | None,
        steps: Iterable[tuple[str, str]],
        target_label: str,
        target_type: str,
        confidence: float,
    ) -> dict:
        chain_steps: list[dict[str, str]] = []
        if source_name:
            chain_steps.append({"label": source_name, "step_type": "node"})
        for label, step_type in steps:
            chain_steps.append({"label": label, "step_type": step_type})
        chain_steps.append({"label": target_label, "step_type": target_type})
        summary = " → ".join(step["label"] for step in chain_steps)
        return {
            "chain_type": target_type,
            "target_type": target_type,
            "target_id": target_label,
            "summary": summary,
            "confidence_percent": round(confidence * 100, 1),
            "steps": chain_steps,
        }

    def build_repository_chain(
        self,
        label: str,
        step_type: str,
        confidence: float,
    ) -> dict:
        summary = label
        return {
            "chain_type": step_type,
            "target_type": step_type,
            "target_id": label,
            "summary": summary,
            "confidence_percent": round(confidence * 100, 1),
            "steps": [{"label": label, "step_type": step_type}],
        }
