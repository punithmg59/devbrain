"""
Evidence Scorer

Calculates aggregate confidence and quality scores for the evidence collection.
"""

from app.services.intent.schemas import Intent
from app.services.repository_intelligence.schemas import (
    EvidenceCollection,
    EvidenceScore,
)


class EvidenceScorer:
    """Calculates coverage, density, relevance, and overall confidence of evidence."""

    def score(self, collection: EvidenceCollection, intent: Intent) -> EvidenceScore:
        """Calculate the overall evidence score."""
        if collection.total_items == 0 and not collection.edges and not collection.workflows:
            return EvidenceScore(
                overall_confidence=0.0,
                coverage_score=0.0,
                density_score=0.0,
                relevance_score=0.0
            )

        coverage = self._calculate_coverage_score(collection, intent)
        density = self._calculate_density_score(collection)
        relevance = self._calculate_relevance_score(collection)

        # Weighted average for overall confidence
        # We heavily weight coverage (did we find what we expected?)
        # and relevance (is it good stuff?)
        overall_confidence = (coverage * 0.5) + (relevance * 0.4) + (density * 0.1)

        return EvidenceScore(
            overall_confidence=round(overall_confidence, 2),
            coverage_score=round(coverage, 2),
            density_score=round(density, 2),
            relevance_score=round(relevance, 2)
        )

    def _calculate_coverage_score(self, collection: EvidenceCollection, intent: Intent) -> float:
        """
        How well does the evidence cover the expectations for this intent?
        Returns 0.0 to 1.0.
        """
        # Determine expected categories based on intent type
        # For simplicity, we define broad expectations
        expected_categories = set()
        
        intent_val = intent.intent.value if hasattr(intent.intent, 'value') else str(intent.intent)
        
        if intent_val in ["delete", "rename", "refactor", "dependency"]:
            expected_categories.update(["caller", "callee", "dependent", "dependency"])
        elif intent_val in ["add_feature", "planning", "architecture"]:
            expected_categories.update(["architecture", "api", "database", "integration_point", "pattern"])
        else:
            expected_categories.update(["reference"])

        populated = set(collection.categories_populated)
        
        # If we have no expected categories, coverage is 1.0 if we found anything, else 0.0
        if not expected_categories:
            return 1.0 if populated else 0.0
            
        # Calculate overlap
        overlap = expected_categories.intersection(populated)
        
        # Penalize slightly for missing expected categories, but not completely
        base_coverage = len(overlap) / len(expected_categories)
        
        # Boost if we found workflows or edges
        if collection.workflows:
            base_coverage += 0.1
        if collection.edges:
            base_coverage += 0.1
            
        return min(base_coverage, 1.0)

    def _calculate_density_score(self, collection: EvidenceCollection) -> float:
        """
        Are there many items per populated category?
        Returns 0.0 to 1.0.
        """
        populated_count = len(collection.categories_populated)
        if populated_count == 0:
            return 0.0
            
        avg_items_per_category = collection.total_items / populated_count
        
        # 5 items per category is considered "good" density
        return min(avg_items_per_category / 5.0, 1.0)

    def _calculate_relevance_score(self, collection: EvidenceCollection) -> float:
        """
        Average relevance score of all items.
        Returns 0.0 to 1.0.
        """
        total_score = 0.0
        count = 0
        
        for items in collection.items.values():
            for item in items:
                total_score += item.relevance_score
                count += 1
                
        for edge in collection.edges:
            total_score += edge.relevance_score
            count += 1
            
        for wf in collection.workflows:
            total_score += wf.relevance_score
            count += 1
            
        if count == 0:
            return 0.0
            
        return min(total_score / count, 1.0)
