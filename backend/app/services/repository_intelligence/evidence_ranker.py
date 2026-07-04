"""
Evidence Ranker

Sorts and truncates evidence items by relevance.
"""

from typing import List

from app.services.repository_intelligence.schemas import (
    EvidenceCollection,
    EvidenceItem,
    EdgeEvidenceItem,
    WorkflowEvidenceItem,
)


class EvidenceRanker:
    """Ranks evidence based on proximity, complexity, and role."""

    def __init__(self, max_per_category: int = 25):
        self.max_per_category = max_per_category

    def rank(self, collection: EvidenceCollection) -> EvidenceCollection:
        """Rank all items in the collection and apply limits."""
        ranked_collection = EvidenceCollection()
        
        # Rank items per category
        for category, items in collection.items.items():
            if not items:
                continue
                
            # Score each item
            for item in items:
                item.relevance_score = self._calculate_item_score(item)
                
            # Sort descending by score
            items.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # Truncate and add to new collection
            ranked_collection.items[category] = items[:self.max_per_category]

        # Rank edges
        for edge in collection.edges:
            edge.relevance_score = min(edge.weight / 10.0, 1.0)  # Normalize weight
        
        collection.edges.sort(key=lambda x: x.relevance_score, reverse=True)
        ranked_collection.edges = collection.edges[:self.max_per_category * 2]
        
        # Rank workflows
        for wf in collection.workflows:
            wf.relevance_score = wf.confidence
            
        collection.workflows.sort(key=lambda x: x.relevance_score, reverse=True)
        ranked_collection.workflows = collection.workflows[:self.max_per_category]

        return ranked_collection

    def _calculate_item_score(self, item: EvidenceItem) -> float:
        """Calculate a relevance score between 0.0 and 1.0."""
        score = 0.0
        
        # 1. Proximity (closer is better)
        if item.graph_distance == 0:
            score += 0.50
        elif item.graph_distance == 1:
            score += 0.30
        elif item.graph_distance == 2:
            score += 0.15
        else:
            score += 0.05
            
        # 2. Complexity (more complex nodes are often more central/important)
        # Assuming complexity_score is typically 0-100, we'll cap its contribution at 0.3
        complexity_contrib = min(item.complexity_score / 100.0, 1.0) * 0.30
        score += complexity_contrib
        
        # 3. Architecture Role
        role = item.architecture_role.lower() if item.architecture_role else ""
        if "service" in role or "controller" in role or "manager" in role:
            score += 0.10
        elif "model" in role or "repository" in role:
            score += 0.05
            
        # 4. Exports and async
        if item.is_exported:
            score += 0.05
        if item.is_async:
            score += 0.05
            
        return min(score, 1.0)
