"""Repository Node Resolution Service - Resolves extracted entities against repository graph."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import RepositoryNode, ResolutionResult, TargetType

logger = logging.getLogger(__name__)


class NodeResolver:
    """Resolves extracted entity names against the repository graph."""

    def __init__(self):
        self.fuzzy_threshold = 0.7  # Minimum similarity for fuzzy match

    async def resolve(
        self,
        db: AsyncSession,
        repo_id: str,
        target_name: str,
        target_type: Optional[TargetType] = None
    ) -> ResolutionResult:
        """
        Resolve a target name against the repository graph.

        Args:
            db: Database session
            repo_id: Repository ID
            target_name: Extracted target name
            target_type: Inferred target type (optional)

        Returns:
            ResolutionResult with resolved node or suggested matches
        """
        # Try exact match first
        result = await self._try_exact_match(db, repo_id, target_name, target_type)
        if result.success:
            return result

        # Try case-insensitive match
        result = await self._try_case_insensitive_match(db, repo_id, target_name, target_type)
        if result.success:
            return result

        # Try fuzzy match
        result = await self._try_fuzzy_match(db, repo_id, target_name, target_type)
        if result.success:
            return result

        # All resolution failed, return suggested matches
        suggested_matches = await self._get_suggested_matches(db, repo_id, target_name, target_type)
        return ResolutionResult(
            node=None,
            success=False,
            match_type="none",
            suggested_matches=suggested_matches,
            error_message=f"Target '{target_name}' not found in repository"
        )

    async def _try_exact_match(
        self,
        db: AsyncSession,
        repo_id: str,
        target_name: str,
        target_type: Optional[TargetType]
    ) -> ResolutionResult:
        """Try exact name match."""
        query = """
            SELECT id, name, node_type, file_path, start_line, end_line
            FROM nodes
            WHERE repo_id = :repo_id
              AND name = :target_name
        """
        params = {"repo_id": repo_id, "target_name": target_name}

        if target_type and target_type != TargetType.UNKNOWN:
            query += " AND node_type = :target_type"
            params["target_type"] = target_type.value

        result = await db.execute(text(query), params)
        row = result.mappings().first()

        if row:
            node = RepositoryNode(
                id=row["id"],
                name=row["name"],
                node_type=TargetType(row["node_type"]),
                file_path=row["file_path"],
                start_line=row["start_line"],
                end_line=row["end_line"],
                repo_id=UUID(repo_id)
            )
            return ResolutionResult(
                node=node,
                success=True,
                match_type="exact",
                suggested_matches=[]
            )

        return ResolutionResult(
            node=None,
            success=False,
            match_type="none",
            suggested_matches=[]
        )

    async def _try_case_insensitive_match(
        self,
        db: AsyncSession,
        repo_id: str,
        target_name: str,
        target_type: Optional[TargetType]
    ) -> ResolutionResult:
        """Try case-insensitive name match."""
        query = """
            SELECT id, name, node_type, file_path, start_line, end_line
            FROM nodes
            WHERE repo_id = :repo_id
              AND LOWER(name) = LOWER(:target_name)
        """
        params = {"repo_id": repo_id, "target_name": target_name}

        if target_type and target_type != TargetType.UNKNOWN:
            query += " AND node_type = :target_type"
            params["target_type"] = target_type.value

        result = await db.execute(text(query), params)
        row = result.mappings().first()

        if row:
            node = RepositoryNode(
                id=row["id"],
                name=row["name"],
                node_type=TargetType(row["node_type"]),
                file_path=row["file_path"],
                start_line=row["start_line"],
                end_line=row["end_line"],
                repo_id=UUID(repo_id)
            )
            return ResolutionResult(
                node=node,
                success=True,
                match_type="case_insensitive",
                suggested_matches=[]
            )

        return ResolutionResult(
            node=None,
            success=False,
            match_type="none",
            suggested_matches=[]
        )

    async def _try_fuzzy_match(
        self,
        db: AsyncSession,
        repo_id: str,
        target_name: str,
        target_type: Optional[TargetType]
    ) -> ResolutionResult:
        """Try fuzzy match using similarity scoring."""
        # Get all nodes and calculate similarity
        query = """
            SELECT id, name, node_type, file_path, start_line, end_line
            FROM nodes
            WHERE repo_id = :repo_id
        """
        params = {"repo_id": repo_id}

        if target_type and target_type != TargetType.UNKNOWN:
            query += " AND node_type = :target_type"
            params["target_type"] = target_type.value

        result = await db.execute(text(query), params)
        rows = result.mappings().all()

        # Find best match using similarity
        best_match = None
        best_similarity = 0.0

        for row in rows:
            similarity = self._calculate_similarity(target_name, row["name"])
            if similarity > best_similarity and similarity >= self.fuzzy_threshold:
                best_similarity = similarity
                best_match = row

        if best_match:
            node = RepositoryNode(
                id=best_match["id"],
                name=best_match["name"],
                node_type=TargetType(best_match["node_type"]),
                file_path=best_match["file_path"],
                start_line=best_match["start_line"],
                end_line=best_match["end_line"],
                repo_id=UUID(repo_id)
            )
            return ResolutionResult(
                node=node,
                success=True,
                match_type="fuzzy",
                suggested_matches=[]
            )

        return ResolutionResult(
            node=None,
            success=False,
            match_type="none",
            suggested_matches=[]
        )

    async def _get_suggested_matches(
        self,
        db: AsyncSession,
        repo_id: str,
        target_name: str,
        target_type: Optional[TargetType]
    ) -> list[dict]:
        """Get suggested matches for failed resolution."""
        query = """
            SELECT id, name, node_type, file_path
            FROM nodes
            WHERE repo_id = :repo_id
        """
        params = {"repo_id": repo_id}

        if target_type and target_type != TargetType.UNKNOWN:
            query += " AND node_type = :target_type"
            params["target_type"] = target_type.value

        result = await db.execute(text(query), params)
        rows = result.mappings().all()

        # Calculate similarity for all nodes and return top 5
        matches = []
        for row in rows:
            similarity = self._calculate_similarity(target_name, row["name"])
            if similarity > 0.3:  # Only include reasonably similar matches
                matches.append({
                    "id": str(row["id"]),
                    "name": row["name"],
                    "node_type": row["node_type"],
                    "file_path": row["file_path"],
                    "similarity": similarity
                })

        # Sort by similarity and return top 5
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return matches[:5]

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using simple heuristic."""
        str1_lower = str1.lower()
        str2_lower = str2.lower()

        # Exact match
        if str1_lower == str2_lower:
            return 1.0

        # Contains match
        if str1_lower in str2_lower or str2_lower in str1_lower:
            return 0.8

        # Levenshtein-like distance (simplified)
        # Count matching characters
        matches = sum(1 for c in str1_lower if c in str2_lower)
        max_len = max(len(str1_lower), len(str2_lower))

        if max_len == 0:
            return 0.0

        similarity = matches / max_len
        return similarity
