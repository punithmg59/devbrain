import logging
import time
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Alias,
    BlastRadiusCache,
    CriticalPath,
    Edge,
    FolderTree,
    ImpactMetric,
    Node,
    Repo,
    RepoFile,
    ResolverLog,
    Workflow,
    WorkflowApi,
    WorkflowFeedback,
    WorkflowFile,
    WorkflowNode,
    WorkflowService,
)

logger = logging.getLogger(__name__)

class RepositoryDeletionService:
    @staticmethod
    async def delete_repository(db: AsyncSession, repo_id: UUID, user_id: UUID) -> None:
        """
        Deletes a repository and all its associated intelligence data.
        Verifies ownership and executes all deletions in a single transaction.
        Uses bulk SQL deletes for maximum performance.
        """
        start_time = time.perf_counter()

        # 1. Verify ownership without loading the full object graph
        repo_query = await db.execute(select(Repo.id, Repo.name).where(Repo.id == repo_id, Repo.user_id == user_id))
        repo_data = repo_query.first()
        
        if not repo_data:
            raise HTTPException(status_code=404, detail="Repository not found or unauthorized")

        logger.info(f"Starting deletion for repository {repo_id} (name: {repo_data.name})")

        try:
            # 2. Find workflow IDs for this repo to delete workflow children
            workflows = await db.execute(select(Workflow.id).where(Workflow.repo_id == repo_id))
            workflow_ids = [w[0] for w in workflows.all()]

            # 3. Delete in correct order (child to parent)
            
            # Edges
            await db.execute(delete(Edge).where(Edge.repo_id == repo_id))
            
            # Workflow children
            if workflow_ids:
                await db.execute(delete(WorkflowFeedback).where(WorkflowFeedback.repo_id == repo_id))
                await db.execute(delete(WorkflowNode).where(WorkflowNode.workflow_id.in_(workflow_ids)))
                await db.execute(delete(WorkflowFile).where(WorkflowFile.workflow_id.in_(workflow_ids)))
                await db.execute(delete(WorkflowApi).where(WorkflowApi.workflow_id.in_(workflow_ids)))
                await db.execute(delete(WorkflowService).where(WorkflowService.workflow_id.in_(workflow_ids)))

            # Workflows
            await db.execute(delete(Workflow).where(Workflow.repo_id == repo_id))

            # Blast radius / Impact metrics
            await db.execute(delete(CriticalPath).where(CriticalPath.repo_id == repo_id))
            await db.execute(delete(ImpactMetric).where(ImpactMetric.repo_id == repo_id))
            await db.execute(delete(BlastRadiusCache).where(BlastRadiusCache.repo_id == repo_id))

            # Resolver logs & Aliases
            await db.execute(delete(ResolverLog).where(ResolverLog.repo_id == repo_id))
            await db.execute(delete(Alias).where(Alias.repo_id == repo_id))

            # Nodes, Folders, Files
            await db.execute(delete(Node).where(Node.repo_id == repo_id))
            await db.execute(delete(FolderTree).where(FolderTree.repo_id == repo_id))
            await db.execute(delete(RepoFile).where(RepoFile.repo_id == repo_id))

            # Finally, the Repo itself
            await db.execute(delete(Repo).where(Repo.id == repo_id))

            # 4. Commit the transaction
            await db.commit()
            
            duration = time.perf_counter() - start_time
            logger.info(f"Successfully deleted repository {repo_id} in {duration:.3f} seconds")

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete repository {repo_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete repository")
