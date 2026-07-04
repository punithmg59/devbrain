"""
Repository Intelligence Engine (Layer 2)

Top-level orchestrator for retrieving engineering evidence.
Consumes Intents from Layer 1, outputs EngineeringEvidence for Layer 3.
"""

import time
import logging
from typing import Dict, Type
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intent.schemas import Intent, IntentType
from app.services.repository_intelligence.schemas import (
    EvidenceCategory,
    EvidenceMetadata,
    EngineeringEvidence,
)
from app.services.repository_intelligence.evidence_collector import (
    EvidenceCollector,
    DeleteEvidenceCollector,
    AddFeatureEvidenceCollector,
    ExplainEvidenceCollector,
    RenameEvidenceCollector,
    RefactorEvidenceCollector,
    DependencyEvidenceCollector,
    ArchitectureEvidenceCollector,
    PlanningEvidenceCollector,
    UnknownEvidenceCollector,
)
from app.services.repository_intelligence.evidence_ranker import EvidenceRanker
from app.services.repository_intelligence.evidence_scorer import EvidenceScorer


logger = logging.getLogger(__name__)


class RepositoryIntelligenceEngine:
    """
    Main orchestration layer for evidence retrieval.
    """

    def __init__(self, max_per_category: int = 25):
        self.max_per_category = max_per_category
        self.ranker = EvidenceRanker(max_per_category=max_per_category)
        self.scorer = EvidenceScorer()

        # Map intent types to collectors
        self._collector_map: Dict[str, Type[EvidenceCollector]] = {
            IntentType.DELETE.value: DeleteEvidenceCollector,
            IntentType.ADD_FEATURE.value: AddFeatureEvidenceCollector,
            IntentType.EXPLAIN.value: ExplainEvidenceCollector,
            IntentType.RENAME.value: RenameEvidenceCollector,
            IntentType.REFACTOR.value: RefactorEvidenceCollector,
            IntentType.DEPENDENCY.value: DependencyEvidenceCollector,
            IntentType.ARCHITECTURE.value: ArchitectureEvidenceCollector,
            IntentType.PLANNING.value: PlanningEvidenceCollector,
            IntentType.UNKNOWN.value: UnknownEvidenceCollector,
        }

    async def collect_evidence(
        self, repo_id: UUID, intent: Intent, db: AsyncSession
    ) -> EngineeringEvidence:
        """
        Collect structured engineering evidence for a given intent.
        
        Args:
            repo_id: The repository ID
            intent: The classified Intent from Layer 1
            db: SQLAlchemy AsyncSession
            
        Returns:
            EngineeringEvidence object
        """
        start_time = time.time()
        intent_val = intent.intent.value if hasattr(intent.intent, 'value') else str(intent.intent)
        
        logger.info(f"Collecting evidence for repo={repo_id}, intent={intent_val}, target={intent.target_name}")

        # 1. Select the correct collector
        collector_class = self._collector_map.get(intent_val, UnknownEvidenceCollector)
        collector = collector_class(
            repo_id=repo_id,
            target_name=intent.target_name,
            target_type=intent.target_type.value if hasattr(intent.target_type, 'value') else str(intent.target_type),
            max_per_category=self.max_per_category,
        )

        # 2. Collect raw evidence
        raw_collection = await collector.collect(db)

        # 3. Rank evidence (truncates and scores items)
        ranked_collection = self.ranker.rank(raw_collection)

        # 4. Score overall collection
        score = self.scorer.score(ranked_collection, intent)

        processing_time_ms = (time.time() - start_time) * 1000

        # 5. Assemble metadata
        metadata = EvidenceMetadata(
            total_nodes_scanned=raw_collection.total_items,  # Approximate
            total_edges_traversed=len(raw_collection.edges),
            total_items_collected=ranked_collection.total_items,
            categories_populated=len(ranked_collection.categories_populated),
            collection_time_ms=round(processing_time_ms, 2),
            collection_methods=[collector.__class__.__name__]
        )

        # 6. Build the final output
        evidence = EngineeringEvidence(
            intent_type=intent_val,
            target_name=intent.target_name,
            target_type=intent.target_type.value if hasattr(intent.target_type, 'value') else str(intent.target_type),
            repo_id=repo_id,
            evidence=ranked_collection,
            score=score,
            metadata=metadata,
            has_callers=bool(ranked_collection.get(EvidenceCategory.CALLER)),
            has_callees=bool(ranked_collection.get(EvidenceCategory.CALLEE)),
            has_tests=bool(ranked_collection.get(EvidenceCategory.TEST)),
            has_apis=bool(ranked_collection.get(EvidenceCategory.API)),
            has_database=bool(ranked_collection.get(EvidenceCategory.DATABASE)),
            has_workflows=bool(ranked_collection.workflows),
            has_critical_paths=bool(ranked_collection.get(EvidenceCategory.CRITICAL_PATH))
        )
        
        logger.info(f"Evidence collection complete in {processing_time_ms:.2f}ms. "
                    f"Confidence: {score.overall_confidence}")

        return evidence
