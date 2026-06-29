import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pipeline.file_scanner import (
    read_file_content,
    ScannedFile,
    ScanResult,
)

if TYPE_CHECKING:
    from app.models.repo import Repo

logger = logging.getLogger(__name__)


@dataclass
class IncrementalPlan:
    is_incremental: bool         # False means full analysis (first run or forced)
    files_to_parse: list[ScannedFile]  # ScannedFile objects that need parsing
    unchanged_paths: set[str]    # rel_paths of files unchanged since last run
    deleted_paths: set[str]      # rel_paths of files present in DB but gone from disk
    total_in_scan: int           # total analyzable files found by scanner
    changed_count: int           # how many files changed or are new
    skipped_count: int           # how many files were skipped (unchanged)


async def build_incremental_plan(
    db: AsyncSession,
    repo_id: str,
    scan_result: ScanResult,
    head_sha: str | None,
) -> IncrementalPlan:
    """
    Compare scanned files against the database to build a parse plan.

    Algorithm:

      STEP 1 — Short-circuit check.
        If repo has no last_commit_sha in DB, this is the first analysis.
        Return IncrementalPlan(is_incremental=False,
                               files_to_parse=scan_result.analyzable, ...)
        All files go into files_to_parse.

      STEP 2 — Head SHA match check.
        If repo.last_commit_sha == head_sha (same commit as last analysis),
        return IncrementalPlan(is_incremental=True,
                               files_to_parse=[],
                               unchanged_paths=all_analyzable_paths, ...)
        Nothing to parse — emit a log message and return immediately.

      STEP 3 — Load existing file hashes from database.
        SELECT file_path, content_hash FROM repo_files
        WHERE repo_id = :repo_id
        Build a dict: prior_hashes = {file_path: content_hash}

      STEP 4 — For each file in scan_result.analyzable:
        Read the file content using read_file_content(sf) to get
        the current content_hash.
        Store the hash on the ScannedFile object as sf.content_hash
        and the content as sf._content (private attribute, used by
        the parser stage to avoid reading twice).

        Compare sf.content_hash to prior_hashes.get(sf.rel_path):
          - If no prior hash OR hash differs → add to files_to_parse
          - If hash matches → add rel_path to unchanged_paths

      STEP 5 — Find deleted files.
        deleted_paths = set(prior_hashes.keys()) - set of all
        scanned analyzable rel_paths.

      STEP 6 — Return IncrementalPlan with all collected data.
    """
    from app.models.repo import Repo
    from app.models.file import RepoFile

    # Load repo to check last_commit_sha
    result = await db.execute(
        select(Repo).where(Repo.id == repo_id)
    )
    repo = result.scalar_one_or_none()

    # STEP 1: Short-circuit - first run
    if not repo or not repo.last_commit_sha:
        logger.info("First analysis for repo %s - full scan", repo_id)
        return IncrementalPlan(
            is_incremental=False,
            files_to_parse=scan_result.analyzable,
            unchanged_paths=set(),
            deleted_paths=set(),
            total_in_scan=scan_result.analyzable_total,
            changed_count=scan_result.analyzable_total,
            skipped_count=0,
        )

    # STEP 2: Head SHA match - no changes
    if head_sha and repo.last_commit_sha == head_sha:
        logger.info("Repo %s unchanged (same SHA %s) - skipping analysis", repo_id, head_sha)
        all_paths = {sf.rel_path for sf in scan_result.analyzable}
        return IncrementalPlan(
            is_incremental=True,
            files_to_parse=[],
            unchanged_paths=all_paths,
            deleted_paths=set(),
            total_in_scan=scan_result.analyzable_total,
            changed_count=0,
            skipped_count=scan_result.analyzable_total,
        )

    # STEP 3: Load existing file hashes
    file_result = await db.execute(
        select(RepoFile.file_path, RepoFile.content_hash)
        .where(RepoFile.repo_id == repo_id)
    )
    prior_hashes = {row[0]: row[1] for row in file_result.all()}

    # STEP 4: Compare files
    files_to_parse: list[ScannedFile] = []
    unchanged_paths: set[str] = set()

    for sf in scan_result.analyzable:
        try:
            content, content_hash = read_file_content(sf)
            sf._content = content
            sf.content_hash = content_hash

            prior_hash = prior_hashes.get(sf.rel_path)
            if prior_hash is None or prior_hash != content_hash:
                files_to_parse.append(sf)
            else:
                unchanged_paths.add(sf.rel_path)
        except Exception as e:
            # If we can't read a file, treat it as changed (needs parsing)
            logger.warning("Failed to read file %s for hash comparison: %s", sf.rel_path, e)
            files_to_parse.append(sf)

    # STEP 5: Find deleted files
    scanned_paths = {sf.rel_path for sf in scan_result.analyzable}
    deleted_paths = set(prior_hashes.keys()) - scanned_paths

    # STEP 6: Return plan
    return IncrementalPlan(
        is_incremental=True,
        files_to_parse=files_to_parse,
        unchanged_paths=unchanged_paths,
        deleted_paths=deleted_paths,
        total_in_scan=scan_result.analyzable_total,
        changed_count=len(files_to_parse),
        skipped_count=len(unchanged_paths),
    )
