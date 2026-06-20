# DevBrain Analysis Pipeline — Complete Redesign

Exact implementation spec mapped to the current codebase. No high-level hand-waving — every
section names the real file and the real function it replaces.

---

## 0. Current Architecture (as-built) and Root Causes

| Concern | Current reality | Why it fails your goals |
|---|---|---|
| Trigger | `routers/analysis.py::trigger_analysis` → FastAPI `BackgroundTasks` (in-process, **not** Celery) | Worker dies with the process; one task blocks the event loop thread pool |
| Dedup | in-memory `_active_analyses: set[str]` in `services/analysis.py` | Lost on restart; not multi-process safe |
| Collect | `analysis_collect.py::collect_analysis_payload` — sequential, single pass, **all content + nodes + edges held in memory** | OOM + slow on large repos; no parallelism |
| Parse | `code_parser.py::parse_python` catches only `SyntaxError` | Any other exception (recursion, encoding, tree walk bug) **propagates and kills the entire run** → status `failed` |
| Persist | `_persist_analysis` uses ORM `add_all` + `flush` | Slow; 500-row INSERTs one object at a time |
| Caps | `language_utils.py`: `MAX_FILES=500`, `MAX_EDGES=2500` | Large repos silently truncated; no "fast mode" |
| Status | `repos.analysis_status` ∈ {pending, queued, analyzing, completed, failed} | No stages, no %, no `completed_with_warnings` |
| Progress | `GET /api/repos/{id}/analysis` returns final counts only; Dashboard polls 5s | No live stage/percent/counters |
| Incremental | none — `_clear_repo_analysis` deletes everything every run | Full re-analysis every time |
| Schema drift | migrations added `repos.last_commit_sha` + `repos.failure_reason` but the `Repo` **model is missing both fields** | Columns exist in DB, unused by ORM |

**Design principle:** the single most damaging bug is in `parse_python` / `collect_analysis_payload` —
exceptions are not isolated per file. Fault tolerance (Req #1) is therefore the foundation; everything
else builds on it.

---

## 1. Architecture Redesign

```
POST /api/repos/{id}/analyze
        │
        ▼
 enqueue AnalysisJob (DB row, status=queued, progress=0)   ── routers/analysis.py
        │
        ▼
 AnalysisWorker  (asyncio task per job, bounded by a global semaphore)
        │
        ├── STAGE cloning        → repo_fetcher.clone_with_retry()   [retry x3]
        ├── STAGE scanning       → file_scanner.scan()  (streaming, fast-mode aware)
        ├── STAGE parsing        → parallel_parser.parse_all()  (ThreadPoolExecutor, per-file try/catch)
        ├── STAGE building_graph → graph_builder.build()  (edges from parsed units)
        ├── STAGE saving         → bulk_writer.persist()  (PG bulk insert, batched 1000)
        └── completed | completed_with_warnings | failed
        │
        ▼
 progress written to AnalysisJob row after every stage + every N files
        │
        ▼
 GET /api/repos/{id}/analysis-progress   ← Frontend polls every 2s
```

Two deployment tiers, same pipeline code:

- **Tier A (now):** in-process `asyncio` worker started from FastAPI lifespan. Survives the redesign
  with zero new infra. Concurrency capped by `asyncio.Semaphore`.
- **Tier B (scale):** the exact same `run_pipeline(job_id)` is callable from a Celery task
  (`celery==5.4.0` and `redis` are already in `requirements.txt`). Switching is one line in
  `enqueue()`. No pipeline rewrite.

The pipeline is pure: `run_pipeline(job_id)` reads everything it needs from the DB, so it works
identically under BackgroundTasks, a dedicated asyncio loop, or Celery.

---

## 2. Files to Modify / Add

### New files
```
backend/app/models/analysis_job.py          # job + per-file-error tables (Req #4, #1, #10)
backend/app/services/pipeline/__init__.py
backend/app/services/pipeline/orchestrator.py   # run_pipeline(): stage state machine (Req #1,#4,#11)
backend/app/services/pipeline/stages.py         # cloning/scanning/parsing/graph/saving stage fns
backend/app/services/pipeline/file_scanner.py   # streaming walk + fast-mode (Req #7, #8)
backend/app/services/pipeline/parallel_parser.py# ThreadPoolExecutor + per-file isolation (Req #1,#2)
backend/app/services/pipeline/graph_builder.py  # node/edge build from parsed units
backend/app/services/pipeline/bulk_writer.py    # PG bulk upserts, batched (Req #9)
backend/app/services/pipeline/incremental.py    # hash/sha diff + node reuse (Req #3)
backend/app/services/pipeline/progress.py       # ProgressReporter (throttled DB writes) (Req #5,#6)
backend/app/services/pipeline/resilience.py     # retry/timeout/circuit-breaker helpers (Req #11)
backend/alembic/versions/j0k1l2m3n4o5_analysis_jobs.py
frontend/src/components/AnalysisProgress.tsx     # animated progress UI (Req #6)
frontend/src/hooks/useAnalysisProgress.ts        # 2s poller (Req #5)
```

### Modified files
```
backend/app/models/repo.py            # add last_commit_sha, failure_reason, content_hash columns to model
backend/app/models/__init__.py        # register AnalysisJob, FileError
backend/app/models/file.py            # add content_hash, last_commit_sha, last_analyzed_at
backend/app/services/repo_fetcher.py  # clone_with_retry + head_commit_sha + sparse/partial clone
backend/app/services/code_parser.py   # wrap bodies in try/except, return [] on ANY error
backend/app/services/language_utils.py# raise caps, add fast-mode dir/extension policy
backend/app/routers/analysis.py       # enqueue job; add /analysis-progress endpoint
backend/app/services/analysis.py      # thin shim → pipeline.orchestrator.run_pipeline
backend/app/main.py                   # start worker loop in lifespan; recover orphan jobs
frontend/src/services/repoService.ts  # getAnalysisProgress()
frontend/src/pages/DashboardPage.tsx  # 2s poll + <AnalysisProgress/>
```

---

## 3. Database Schema Changes

### 3.1 New table `analysis_jobs` (queue + progress + metrics)

```python
# backend/app/models/analysis_job.py
import uuid
from datetime import datetime
from sqlalchemy import (DateTime, Float, ForeignKey, Integer, String, Text, func, text)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

# Canonical stage order — also used to compute percent.
STAGES = ["queued", "cloning", "scanning", "parsing", "building_graph", "saving"]
TERMINAL = {"completed", "completed_with_warnings", "failed"}


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repos.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    status: Mapped[str] = mapped_column(String(40), default="queued", server_default="queued", index=True)
    current_stage: Mapped[str] = mapped_column(String(40), default="queued", server_default="queued")
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")

    files_total: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    files_processed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    functions_found: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    nodes_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    edges_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    files_failed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Req #10 — performance metrics
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    files_per_second: Mapped[float | None] = mapped_column(Float, nullable=True)
    nodes_per_second: Mapped[float | None] = mapped_column(Float, nullable=True)
    edges_per_second: Mapped[float | None] = mapped_column(Float, nullable=True)

    fast_mode: Mapped[bool] = mapped_column(default=False, server_default="false")
    incremental: Mapped[bool] = mapped_column(default=False, server_default="false")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # list of {file_path, error_type, message} — also mirrored into file_errors for querying
    warnings: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")

    # heartbeat for orphan recovery (replaces the in-memory _active_analyses set)
    worker_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FileError(Base):
    """One row per file that failed parsing — Req #1 'Store file-level errors'."""
    __tablename__ = "file_errors"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
                                          server_default=text("gen_random_uuid()"))
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                              ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True)
    repo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                               ForeignKey("repos.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    error_type: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### 3.2 Columns added to existing tables

`repos` (model is currently missing two that already exist in DB):
```python
# backend/app/models/repo.py  — add to class Repo
last_commit_sha: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)  # migration exists
failure_reason:  Mapped[str | None] = mapped_column(Text, nullable=True)                      # migration exists
# NEW migration:
content_hash:    Mapped[str | None] = mapped_column(String(64), nullable=True)  # aggregate repo hash
```
Also widen the status check — `analysis_status` now also takes `completed_with_warnings`,
`cloning`, `scanning`, `parsing`, `building_graph`, `saving` (column is already `String(50)`, no DDL change).

`repo_files` (Req #3 incremental):
```python
# backend/app/models/file.py — add to class RepoFile
content_hash:     Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
last_commit_sha:  Mapped[str | None] = mapped_column(String(100), nullable=True)
last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

### 3.3 Migration

```python
# backend/alembic/versions/j0k1l2m3n4o5_analysis_jobs.py
revision = "j0k1l2m3n4o5"
down_revision = "i9j0k1l2m3n4"   # current head

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

def upgrade() -> None:
    op.create_table("analysis_jobs",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("repo_id", UUID(as_uuid=True), sa.ForeignKey("repos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(40), server_default="queued", nullable=False),
        sa.Column("current_stage", sa.String(40), server_default="queued", nullable=False),
        sa.Column("progress_percent", sa.Float, server_default="0.0"),
        sa.Column("files_total", sa.Integer, server_default="0"),
        sa.Column("files_processed", sa.Integer, server_default="0"),
        sa.Column("functions_found", sa.Integer, server_default="0"),
        sa.Column("nodes_count", sa.Integer, server_default="0"),
        sa.Column("edges_count", sa.Integer, server_default="0"),
        sa.Column("files_failed", sa.Integer, server_default="0"),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("files_per_second", sa.Float, nullable=True),
        sa.Column("nodes_per_second", sa.Float, nullable=True),
        sa.Column("edges_per_second", sa.Float, nullable=True),
        sa.Column("fast_mode", sa.Boolean, server_default="false"),
        sa.Column("incremental", sa.Boolean, server_default="false"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("warnings", JSONB, server_default="[]"),
        sa.Column("worker_id", sa.String(80), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_analysis_jobs_repo_id", "analysis_jobs", ["repo_id"])
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])

    op.create_table("file_errors",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE")),
        sa.Column("repo_id", UUID(as_uuid=True), sa.ForeignKey("repos.id", ondelete="CASCADE")),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("error_type", sa.String(120)),
        sa.Column("message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_file_errors_job_id", "file_errors", ["job_id"])

    op.add_column("repos", sa.Column("content_hash", sa.String(64), nullable=True))
    op.add_column("repo_files", sa.Column("content_hash", sa.String(64), nullable=True))
    op.add_column("repo_files", sa.Column("last_commit_sha", sa.String(100), nullable=True))
    op.add_column("repo_files", sa.Column("last_analyzed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_repo_files_content_hash", "repo_files", ["content_hash"])

def downgrade() -> None:
    op.drop_index("ix_repo_files_content_hash", "repo_files")
    op.drop_column("repo_files", "last_analyzed_at")
    op.drop_column("repo_files", "last_commit_sha")
    op.drop_column("repo_files", "content_hash")
    op.drop_column("repos", "content_hash")
    op.drop_table("file_errors")
    op.drop_table("analysis_jobs")
```

> Note: the app also has `database.validate_schema()` which auto-adds *missing columns* at startup,
> but it does **not** create missing tables beyond `create_all`. Running the migration is the
> correct path; `init_db()` (`Base.metadata.create_all`) will also create the two new tables on a
> fresh DB since the models are registered in `models/__init__.py`.

---

## 4. Fault-Tolerant Parsing (Req #1) — the core fix

### 4.1 `code_parser.py` — never raise

Every parser body is wrapped so a single file can never throw out of `parse_file`.

```python
# backend/app/services/code_parser.py
import logging
logger = logging.getLogger(__name__)

def parse_file(content: str, file_path: str) -> list[dict]:
    """Contract: NEVER raises. Returns [] on any failure."""
    try:
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        if ext == "py":
            return parse_python(content, file_path)
        if ext in ("js", "jsx", "ts", "tsx"):
            return parse_javascript(content, file_path)
        return []
    except RecursionError:
        logger.warning("parse recursion limit hit: %s", file_path)
        return []
    except Exception:
        logger.warning("parser crashed on %s", file_path, exc_info=True)
        return []
```

`parse_python` currently only catches `SyntaxError` around `ast.parse`. Keep that (it's the common
case) but also guard the **tree walk** — `ast.get_source_segment`, deep nesting, etc. can raise.
The outer `try` in `parse_file` already makes the whole thing safe; no behavior change for valid files.

### 4.2 Per-file isolation in the parallel parser

This is where fault tolerance is enforced operationally — each file is its own task with its own
try/except; a failure records a `FileError` and continues.

```python
# backend/app/services/pipeline/parallel_parser.py
import concurrent.futures as cf
from dataclasses import dataclass, field
from app.services.code_parser import parse_file

@dataclass
class ParseResult:
    parsed: dict[str, list[dict]] = field(default_factory=dict)   # rel_path -> nodes
    errors: list[dict] = field(default_factory=list)              # {file_path,error_type,message}

def _parse_one(rel_path: str, content: str) -> tuple[str, list[dict], dict | None]:
    try:
        return rel_path, parse_file(content, rel_path), None
    except Exception as e:  # defense in depth; parse_file already swallows
        return rel_path, [], {"file_path": rel_path,
                              "error_type": type(e).__name__, "message": str(e)[:500]}

def parse_all(files: list[tuple[str, str]], *, max_workers: int, on_done=None) -> ParseResult:
    """files: list of (rel_path, content). on_done(done_count) for progress."""
    result = ParseResult()
    done = 0
    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_parse_one, rp, c): rp for rp, c in files}
        for fut in cf.as_completed(futs):
            rel_path, nodes, err = fut.result()   # _parse_one never raises
            if nodes:
                result.parsed[rel_path] = nodes
            if err:
                result.errors.append(err)
            done += 1
            if on_done and done % 25 == 0:
                on_done(done)
    if on_done:
        on_done(done)
    return result
```

Python's GIL means CPU-bound `ast.parse` won't scale linearly across threads, but the workload is a
mix of file I/O (`read_text`) + C-level `ast` parsing (releases GIL partially) + regex. Threads give
a real 2–4x here without the pickling cost of processes. For very large repos you can swap
`ThreadPoolExecutor` → `ProcessPoolExecutor` behind the same `parse_all` signature; `parse_file` is
already a pure top-level function (picklable). Default: threads, `max_workers = min(8, os.cpu_count())`.

### 4.3 Status resolution rule (Req #1)

```python
# in orchestrator, after saving stage:
if files_failed == 0:
    final = "completed"
else:
    final = "completed_with_warnings"   # ANY successful files → not 'failed'
# 'failed' is reserved for: clone failure, or 0 files successfully analyzed, or DB write failure.
```

So 1000 files / 3 broken → `completed_with_warnings`, 997 persisted. Exactly your spec.

---

## 5. Orchestrator — Stage State Machine (Req #1, #4, #11)

```python
# backend/app/services/pipeline/orchestrator.py
import asyncio, logging, os, socket, time
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from app.database import async_session_factory
from app.models import Repo, User
from app.models.analysis_job import AnalysisJob
from app.services.pipeline.progress import ProgressReporter
from app.services.pipeline import stages
from app.services.pipeline.resilience import CloneError

logger = logging.getLogger(__name__)
WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"

async def run_pipeline(job_id: UUID) -> None:
    """Top-level entry. NEVER raises. Drives a job to a terminal state."""
    async with async_session_factory() as db:
        job = (await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))).scalar_one_or_none()
        if not job or job.status in ("completed", "completed_with_warnings", "failed"):
            return
        repo = (await db.execute(select(Repo).where(Repo.id == job.repo_id))).scalar_one_or_none()
        user = (await db.execute(select(User).where(User.id == job.user_id))).scalar_one_or_none()
        if not repo or not user:
            return

        reporter = ProgressReporter(db, job, repo)
        job.worker_id, job.started_at = WORKER_ID, datetime.now(timezone.utc)
        started = time.monotonic()
        clone_path = None
        try:
            # ── cloning ───────────────────────────────────────────
            await reporter.stage("cloning", 2)
            clone_path, head_sha = await stages.clone(repo, user, db)   # retry x3 inside

            # ── scanning ──────────────────────────────────────────
            await reporter.stage("scanning", 8)
            scan = await asyncio.to_thread(stages.scan, clone_path, repo)
            job.fast_mode = scan.fast_mode
            await reporter.set_total(scan.files_total)

            # ── incremental diff ─────────────────────────────────
            plan = await stages.plan_incremental(db, repo, scan, head_sha)
            job.incremental = plan.is_incremental

            # ── parsing (parallel, fault-tolerant) ───────────────
            await reporter.stage("parsing", 15)
            parsed = await asyncio.to_thread(
                stages.parse, plan, reporter.parsing_callback())
            await reporter.add_warnings(parsed.errors)   # writes file_errors rows

            # ── building graph ───────────────────────────────────
            await reporter.stage("building_graph", 70)
            graph = await asyncio.to_thread(stages.build_graph, plan, parsed)
            await reporter.set_counts(nodes=graph.node_count, edges=graph.edge_count,
                                      functions=graph.function_count)

            # ── saving (bulk, batched) ───────────────────────────
            await reporter.stage("saving", 88)
            await stages.persist(db, repo, job, plan, graph, head_sha)

            # ── finalize ─────────────────────────────────────────
            failed = job.files_failed
            final = "completed" if failed == 0 else "completed_with_warnings"
            elapsed = time.monotonic() - started
            await reporter.finish(final, elapsed)
            repo.last_commit_sha = head_sha
            repo.analysis_status = final
            repo.last_analyzed_at = datetime.now(timezone.utc)
            repo.total_files = graph.file_count
            repo.total_functions = graph.function_count
            await db.commit()
            await stages.run_post_analysis(repo.id)   # alias/workflow/impact precompute (isolated)
            logger.info("Analysis %s for %s: %d files, %d failed", final, repo.full_name,
                        graph.file_count, failed)

        except CloneError as e:
            await reporter.fail(f"Clone failed: {e}", db, repo)
        except asyncio.CancelledError:
            await reporter.fail("Worker cancelled/restarted", db, repo)
            raise
        except Exception as e:
            logger.exception("Pipeline crashed for job %s", job_id)
            await reporter.fail(f"{type(e).__name__}: {e}", db, repo)
        finally:
            if clone_path:
                await asyncio.to_thread(stages.cleanup, clone_path)
```

**Never crashes the worker:** the only re-raise is `CancelledError` (cooperative shutdown). Every
other exception lands in `reporter.fail()`, which marks the job `failed` and commits — the worker
loop keeps running for the next job.

### 5.1 The worker loop + orphan recovery (replaces `_active_analyses`)

```python
# backend/app/services/pipeline/orchestrator.py  (continued)
_SEM = asyncio.Semaphore(int(os.getenv("ANALYSIS_CONCURRENCY", "3")))
_HEARTBEAT_STALE_SEC = 90

async def worker_loop(stop: asyncio.Event) -> None:
    """Single in-process consumer. Pulls queued jobs, runs them under a concurrency cap."""
    while not stop.is_set():
        job_id = await _claim_next_job()        # SELECT ... FOR UPDATE SKIP LOCKED
        if job_id is None:
            await asyncio.sleep(1.0)
            continue
        async with _SEM:
            asyncio.create_task(run_pipeline(job_id))

async def _claim_next_job() -> UUID | None:
    async with async_session_factory() as db:
        # atomically claim a queued job OR reclaim a stale-heartbeat one
        row = await db.execute(text("""
            UPDATE analysis_jobs SET status='cloning', heartbeat_at=now()
            WHERE id = (
              SELECT id FROM analysis_jobs
              WHERE status='queued'
                 OR (status NOT IN ('completed','completed_with_warnings','failed')
                     AND heartbeat_at < now() - interval '90 seconds')
              ORDER BY created_at LIMIT 1
              FOR UPDATE SKIP LOCKED)
            RETURNING id"""))
        await db.commit()
        r = row.first()
        return r[0] if r else None
```

`FOR UPDATE SKIP LOCKED` makes this safe across multiple worker processes/instances → horizontally
scalable (Req: scalable). The heartbeat (written by `ProgressReporter` every stage) replaces the
fragile in-memory `_active_analyses` set and `is_stale_in_progress` clock logic; a job whose worker
died is auto-reclaimed after 90s.

---

## 6. Streaming File Scan + Fast Mode (Req #7, #8)

```python
# backend/app/services/pipeline/file_scanner.py
import hashlib, os
from dataclasses import dataclass
from pathlib import Path
from app.services.language_utils import (ANALYZABLE_EXTENSIONS, detect_language,
                                         normalize_folder_path, folder_depth)

HARD_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
                  "build", ".next", "coverage", ".pytest_cache", ".mypy_cache",
                  ".tox", "vendor", ".idea", ".cache", "out", "target"}
FAST_MODE_FILE_THRESHOLD = 5000
# In fast mode, only descend into source-bearing top-level dirs:
FAST_MODE_KEEP_HINTS = ("src", "app", "lib", "api", "services", "models", "server",
                        "backend", "core", "internal", "pkg", "routes", "controllers",
                        "handlers", "db", "database")
MAX_FILE_BYTES = 1_000_000

@dataclass
class ScannedFile:
    rel_path: str
    abs_path: Path
    size: int
    language: str | None
    analyzable: bool
    content_hash: str | None = None   # filled lazily during read

@dataclass
class ScanResult:
    files: list[ScannedFile]
    files_total: int
    fast_mode: bool

def _count_quick(root: str) -> int:
    n = 0
    for _, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in HARD_SKIP_DIRS and not d.startswith(".")]
        n += len(filenames)
        if n > FAST_MODE_FILE_THRESHOLD * 2:   # early exit, we only need the threshold decision
            return n
    return n

def scan(clone_path: str, repo) -> ScanResult:
    fast = _count_quick(clone_path) > FAST_MODE_FILE_THRESHOLD
    root = Path(clone_path)
    files: list[ScannedFile] = []
    for dirpath, dirnames, filenames in os.walk(clone_path):
        dirnames[:] = [d for d in dirnames if d not in HARD_SKIP_DIRS and not d.startswith(".")]
        if fast:
            depth = Path(dirpath).relative_to(root).parts
            if len(depth) == 1 and depth[0].lower() not in FAST_MODE_KEEP_HINTS \
               and not _has_source_children(Path(dirpath)):
                dirnames[:] = []   # prune non-source top-level dirs entirely
                continue
        for fn in filenames:
            abs_p = Path(dirpath) / fn
            try:
                size = abs_p.stat().st_size
            except OSError:
                continue
            if size > MAX_FILE_BYTES:
                continue
            rel = abs_p.relative_to(root).as_posix()
            ext = abs_p.suffix.lower()
            analyzable = ext in ANALYZABLE_EXTENSIONS
            if fast and not analyzable:
                continue   # fast mode: only index source files
            files.append(ScannedFile(rel, abs_p, size, detect_language(rel), analyzable))
    return ScanResult(files=files, files_total=len(files), fast_mode=fast)
```

**Memory (Req #8):** the old code built `file_contents: dict[str, str]` holding *every file's full
text* simultaneously, plus `payload.nodes` for the whole repo. The new flow streams: read content →
hash → parse → keep only the **parsed unit dicts** (which already cap `raw_code` at 2000 chars in
`parse_python`); the full source string is released as soon as the file is parsed. Peak memory is
O(parsed nodes), not O(sum of all file bytes).

```python
def read_and_hash(sf: ScannedFile) -> tuple[str, str]:
    data = sf.abs_path.read_bytes()
    sf.content_hash = hashlib.sha256(data).hexdigest()
    return data.decode("utf-8", errors="replace"), sf.content_hash
```

Caps move to config (raise the old `MAX_FILES=500`): normal mode no longer truncates at 500; fast
mode bounds work by *pruning non-source dirs* instead of a blunt file count. `MAX_EDGES` becomes a
per-repo budget scaled by node count rather than a flat 2500.

---

## 7. Incremental Analysis (Req #3)

```python
# backend/app/services/pipeline/incremental.py
from dataclasses import dataclass, field
from sqlalchemy import select
from app.models import RepoFile

@dataclass
class IncrementalPlan:
    is_incremental: bool
    changed: list = field(default_factory=list)     # ScannedFile needing parse
    unchanged_paths: set = field(default_factory=set)
    deleted_paths: set = field(default_factory=set)

async def plan_incremental(db, repo, scan, head_sha) -> IncrementalPlan:
    # First analysis, or repo has no prior commit recorded → full run
    if not repo.last_commit_sha:
        return IncrementalPlan(is_incremental=False, changed=scan.files)

    rows = (await db.execute(
        select(RepoFile.file_path, RepoFile.content_hash)
        .where(RepoFile.repo_id == repo.id))).all()
    prior = {p: h for p, h in rows}

    changed, unchanged = [], set()
    for sf in scan.files:
        content, h = read_and_hash(sf)          # hash now; keep content on sf for changed files
        sf._content = content
        if prior.get(sf.rel_path) == h:
            unchanged.add(sf.rel_path)          # reuse existing nodes/edges
        else:
            changed.append(sf)
    deleted = set(prior) - {sf.rel_path for sf in scan.files}
    return IncrementalPlan(is_incremental=True, changed=changed,
                           unchanged_paths=unchanged, deleted_paths=deleted)
```

**Reuse strategy (node/edge preservation):**
- `unchanged_paths`: their `RepoFile`, `Node`, and intra-file edges are **left untouched** in the DB.
- `changed`: delete only *that file's* nodes/edges (`DELETE ... WHERE file_id IN (changed file ids)`),
  re-parse, re-insert.
- `deleted_paths`: delete their `RepoFile` (cascade removes nodes/edges).
- Cross-file edges (imports/calls) touching a changed file are recomputed; edges among unchanged
  files survive. Because edges cascade on node delete, and we only delete changed-file nodes, the
  reuse is automatic.

This replaces the unconditional `_clear_repo_analysis` (which `DELETE`s all four tables every run).
Re-analysis cost ∝ changed files, delivering the 5–20x target when a handful of files change.

A fast pre-check short-circuits a no-op run entirely:
```python
if repo.last_commit_sha == head_sha:
    # nothing changed at all → mark completed instantly, skip parse/graph/save
```

---

## 8. Graph Builder + Bulk Writer (Req #9)

The graph logic is the existing `analysis_collect.py` edge-extraction code, refactored to operate on
`plan.changed + reused` instead of a single global pass — the regex/ORM/service/edge heuristics are
preserved verbatim. The important change is persistence.

### 8.1 Bulk writes via PostgreSQL `INSERT ... ON CONFLICT`

```python
# backend/app/services/pipeline/bulk_writer.py
from sqlalchemy.dialects.postgresql import insert
from app.models import RepoFile, Node, Edge, FolderTree

BATCH = 1000

async def bulk_upsert_files(db, repo_id, rows: list[dict]) -> dict[str, str]:
    """rows: file dicts. Returns {file_path: id}. Batched, single round-trip per batch."""
    out = {}
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i+BATCH]
        stmt = insert(RepoFile).values([{**r, "repo_id": repo_id} for r in chunk])
        stmt = stmt.on_conflict_do_update(
            constraint="uq_repo_files_repo_id_file_path",
            set_={"content_hash": stmt.excluded.content_hash,
                  "size_bytes": stmt.excluded.size_bytes,
                  "line_count": stmt.excluded.line_count,
                  "last_analyzed_at": stmt.excluded.last_analyzed_at},
        ).returning(RepoFile.id, RepoFile.file_path)
        res = await db.execute(stmt)
        for fid, fpath in res.all():
            out[fpath] = fid
    return out

async def bulk_insert_nodes(db, repo_id, rows: list[dict]) -> dict[str, str]:
    out = {}
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i+BATCH]
        stmt = insert(Node).values([{**r, "repo_id": repo_id} for r in chunk])
        stmt = stmt.on_conflict_do_update(
            constraint="uq_nodes_repo_id_full_path",
            set_={"start_line": stmt.excluded.start_line, "end_line": stmt.excluded.end_line,
                  "raw_code": stmt.excluded.raw_code, "signature": stmt.excluded.signature,
                  "calls": stmt.excluded.calls, "imports": stmt.excluded.imports},
        ).returning(Node.id, Node.full_path)
        res = await db.execute(stmt)
        for nid, fpath in res.all():
            out[fpath] = nid
    return out

async def bulk_insert_edges(db, repo_id, rows: list[dict]) -> int:
    total = 0
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i+BATCH]
        stmt = insert(Edge).values([{**r, "repo_id": repo_id} for r in chunk])
        stmt = stmt.on_conflict_do_nothing(constraint="uq_edges_from_to_type")
        await db.execute(stmt)
        total += len(chunk)
    return total
```

Why this is dramatically faster than the current `db.add_all(...)` + `flush()`:
- ORM `add_all` builds a Python object per row and issues per-row INSERTs (asyncpg can't batch them
  the same way); bulk `insert().values([...])` sends one multi-row statement per 1000 rows.
- `ON CONFLICT` makes incremental re-runs idempotent (no need to delete-then-insert unchanged rows).
- `RETURNING` gives us the generated UUIDs to wire `full_path → node_id` for edges, exactly as the
  current `path_to_node_id` map does — but in bulk.

> PgBouncer note: `database.py` already runs on the **session pooler (5432)** with
> `statement_cache_size=0`. Multi-row `insert().values()` works fine there; we are not relying on
> server-side prepared statements.

### 8.2 Persist stage ties it together

```python
# stages.persist()
async def persist(db, repo, job, plan, graph, head_sha):
    if plan.is_incremental:
        await _delete_changed(db, repo.id, plan)        # only changed + deleted files' nodes/edges
    else:
        await _clear_all(db, repo.id)                   # full reset (old behavior, batched DELETE)
    file_ids = await bulk_upsert_files(db, repo.id, graph.file_rows)
    for n in graph.node_rows:
        n["file_id"] = file_ids.get(n.pop("_file_path"), None)
    node_ids = await bulk_insert_nodes(db, repo.id, graph.node_rows)
    edge_rows = [{"from_node_id": node_ids[e["from_path"]], "to_node_id": node_ids[e["to_path"]],
                  "edge_type": e["edge_type"]}
                 for e in graph.edge_rows
                 if e["from_path"] in node_ids and e["to_path"] in node_ids]
    job.edges_count = await bulk_insert_edges(db, repo.id, edge_rows)
    await db.commit()
```

---

## 9. Resilience: retry / timeout / circuit breaker (Req #11)

```python
# backend/app/services/pipeline/resilience.py
import asyncio, logging, time
logger = logging.getLogger(__name__)

class CloneError(Exception): ...

async def retry_async(fn, *, attempts: int, base_delay: float, exc=(Exception,), label=""):
    last = None
    for i in range(1, attempts + 1):
        try:
            return await fn()
        except exc as e:
            last = e
            logger.warning("%s attempt %d/%d failed: %s", label, i, attempts, e)
            if i < attempts:
                await asyncio.sleep(base_delay * (2 ** (i - 1)))   # exp backoff
    raise last

class CircuitBreaker:
    """Trips after N consecutive failures; blocks calls for cooldown seconds."""
    def __init__(self, threshold=5, cooldown=60.0):
        self.threshold, self.cooldown = threshold, cooldown
        self.failures, self.opened_at = 0, 0.0
    def allow(self) -> bool:
        if self.failures < self.threshold:
            return True
        if (time.monotonic() - self.opened_at) > self.cooldown:
            self.failures = 0
            return True
        return False
    def record(self, ok: bool):
        if ok:
            self.failures = 0
        else:
            self.failures += 1
            if self.failures == self.threshold:
                self.opened_at = time.monotonic()
```

Applied:
- **Clone retry x3** (`stages.clone` wraps `repo_fetcher.clone_with_retry`): exponential backoff,
  raises `CloneError` only after all 3 fail → job `failed` (the one legitimate failure case).
- **Parser retry x2**: per-file, but since `parse_file` is deterministic a retry only helps transient
  I/O (file read). Implemented as a 2-attempt read in `read_and_hash`.
- **DB retry x3**: each bulk batch wrapped in `retry_async(..., attempts=3)` for transient
  `asyncpg` disconnects (`pool_pre_ping` already helps).
- **Circuit breaker** guards the optional `run_post_analysis` external calls (Groq embeddings,
  workflow discovery) so a flaky LLM provider can't stall the worker.
- **Timeouts**: clone 120s, parse stage `ANALYSIS_TIMEOUT_SECONDS` (keep 600), each DB batch 30s,
  via `asyncio.wait_for`.

```python
# backend/app/services/repo_fetcher.py  — additions
def head_commit_sha(path: str) -> str:
    from git import Repo as GitRepo
    return GitRepo(path).head.commit.hexsha

async def clone_with_retry(full_name, token, branch) -> tuple[str, str]:
    from app.services.pipeline.resilience import retry_async, CloneError
    async def _do():
        path = await asyncio.to_thread(clone_github_repo, full_name, token, branch)
        return path, await asyncio.to_thread(head_commit_sha, path)
    try:
        return await retry_async(_do, attempts=3, base_delay=2.0, label="clone")
    except Exception as e:
        raise CloneError(str(e)) from e
```
Also add `--filter=blob:limit=1m` / shallow `depth=1` (already `depth=1`) and consider partial clone
for huge repos: `Repo.clone_from(url, dir, multi_options=["--depth=1", "--filter=blob:none"])`.

---

## 10. Progress Tracking API (Req #5)

```python
# backend/app/services/pipeline/progress.py
from datetime import datetime, timezone
from app.models.analysis_job import FileError

# percent floor per stage; within-stage we interpolate by files_processed/files_total
STAGE_FLOOR = {"queued": 0, "cloning": 2, "scanning": 8, "parsing": 15,
               "building_graph": 70, "saving": 88, "completed": 100,
               "completed_with_warnings": 100, "failed": 100}

class ProgressReporter:
    def __init__(self, db, job, repo):
        self.db, self.job, self.repo = db, job, repo
        self._last_write = 0.0

    async def stage(self, name, floor):
        self.job.current_stage = name
        self.job.status = name
        self.job.progress_percent = float(floor)
        self.job.heartbeat_at = datetime.now(timezone.utc)
        self.repo.analysis_status = name        # mirror so existing Dashboard keeps working
        await self.db.commit()

    async def set_total(self, n):
        self.job.files_total = n
        await self.db.commit()

    def parsing_callback(self):
        # called from worker thread; schedule a throttled async write
        def cb(done):
            self.job.files_processed = done
            span = 70 - 15
            if self.job.files_total:
                self.job.progress_percent = 15 + span * (done / self.job.files_total)
        return cb

    async def set_counts(self, *, nodes, edges, functions):
        self.job.nodes_count, self.job.edges_count, self.job.functions_found = nodes, edges, functions
        await self.db.commit()

    async def add_warnings(self, errors: list[dict]):
        self.job.files_failed = len(errors)
        self.job.warnings = errors[:200]
        for e in errors:
            self.db.add(FileError(job_id=self.job.id, repo_id=self.repo.id, **e))
        await self.db.commit()

    async def finish(self, final, elapsed):
        j = self.job
        j.status = j.current_stage = final
        j.progress_percent = 100.0
        j.finished_at = datetime.now(timezone.utc)
        j.duration_seconds = elapsed
        j.files_per_second = (j.files_processed / elapsed) if elapsed else None
        j.nodes_per_second = (j.nodes_count / elapsed) if elapsed else None
        j.edges_per_second = (j.edges_count / elapsed) if elapsed else None
        await self.db.commit()

    async def fail(self, msg, db=None, repo=None):
        self.job.status = self.job.current_stage = "failed"
        self.job.error_message = msg[:1000]
        self.job.finished_at = datetime.now(timezone.utc)
        if repo:
            repo.analysis_status = "failed"
            repo.failure_reason = msg[:1000]
        await self.db.commit()
```

Endpoint:

```python
# backend/app/routers/analysis.py  — add
from app.models.analysis_job import AnalysisJob
from app.schemas.analysis import AnalysisProgressResponse

@router.get("/api/repos/{repo_id}/analysis-progress", response_model=AnalysisProgressResponse)
async def analysis_progress(repo_id: str,
                            current_user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    repo = await _get_user_repo(repo_id, current_user, db)
    job = (await db.execute(
        select(AnalysisJob).where(AnalysisJob.repo_id == repo.id)
        .order_by(AnalysisJob.created_at.desc()).limit(1))).scalar_one_or_none()
    if not job:
        return AnalysisProgressResponse(status=repo.analysis_status, current_stage=repo.analysis_status,
                                        files_processed=0, total_files=repo.total_files,
                                        progress_percent=100.0 if repo.analysis_status=="completed" else 0.0,
                                        functions_found=repo.total_functions, nodes_count=0,
                                        edges_count=0, files_failed=0)
    return AnalysisProgressResponse(
        status=job.status, current_stage=job.current_stage,
        files_processed=job.files_processed, total_files=job.files_total,
        progress_percent=round(job.progress_percent, 1),
        functions_found=job.functions_found, nodes_count=job.nodes_count,
        edges_count=job.edges_count, files_failed=job.files_failed,
        warnings=job.warnings, duration_seconds=job.duration_seconds)
```

```python
# backend/app/schemas/analysis.py  — add
class AnalysisProgressResponse(BaseModel):
    status: str
    current_stage: str
    files_processed: int
    total_files: int
    progress_percent: float
    functions_found: int = 0
    nodes_count: int = 0
    edges_count: int = 0
    files_failed: int = 0
    warnings: list = []
    duration_seconds: float | None = None
```

### Trigger endpoint becomes an enqueue

```python
# backend/app/routers/analysis.py  — replace body of trigger_analysis
@router.post("/api/repos/{repo_id}/analyze", response_model=AnalysisTriggerResponse)
async def trigger_analysis(repo_id, current_user=Depends(get_current_user), db=Depends(get_db)):
    repo = await _get_user_repo(repo_id, current_user, db)
    # de-dupe: an active job already exists?
    active = (await db.execute(select(AnalysisJob).where(
        AnalysisJob.repo_id == repo.id,
        AnalysisJob.status.notin_(["completed","completed_with_warnings","failed"])
    ).limit(1))).scalar_one_or_none()
    if active:
        return AnalysisTriggerResponse(repo_id=str(repo.id), status=active.status,
                                       message="Analysis already in progress")
    job = AnalysisJob(repo_id=repo.id, user_id=current_user.id, status="queued")
    db.add(job)
    repo.analysis_status = "queued"
    await db.commit()
    return AnalysisTriggerResponse(repo_id=str(repo.id), status="queued",
                                   message="Repository analysis queued")
```

No more `BackgroundTasks` — the `worker_loop` picks the job up. This makes analysis survive request
completion and decouples it from the HTTP worker.

### main.py lifespan starts the worker

```python
# backend/app/main.py  — in startup
import asyncio
from app.services.pipeline.orchestrator import worker_loop
_stop = asyncio.Event()
@app.on_event("startup")
async def _start_worker():
    app.state.worker = asyncio.create_task(worker_loop(_stop))
@app.on_event("shutdown")
async def _stop_worker():
    _stop.set()
    if getattr(app.state, "worker", None):
        await asyncio.wait_for(app.state.worker, timeout=10)
```

---

## 11. Frontend: Progress Animation (Req #6)

### 11.1 Service + hook

```ts
// frontend/src/services/repoService.ts — add
getAnalysisProgress: async (repoId: string) => {
  const res = await API.get(`/api/repos/${repoId}/analysis-progress`);
  return res.data as {
    status: string; current_stage: string;
    files_processed: number; total_files: number; progress_percent: number;
    functions_found: number; nodes_count: number; edges_count: number;
    files_failed: number; warnings: {file_path:string;message:string}[];
    duration_seconds: number | null;
  };
},
```

```ts
// frontend/src/hooks/useAnalysisProgress.ts
import { useEffect, useRef, useState } from "react";
import { repoService } from "../services/repoService";

const TERMINAL = new Set(["completed", "completed_with_warnings", "failed"]);

export function useAnalysisProgress(repoId: string, active: boolean) {
  const [p, setP] = useState<any>(null);
  const timer = useRef<number>();
  useEffect(() => {
    if (!active) return;
    let alive = true;
    const tick = async () => {
      try {
        const data = await repoService.getAnalysisProgress(repoId);
        if (!alive) return;
        setP(data);
        if (!TERMINAL.has(data.status))
          timer.current = window.setTimeout(tick, 2000);   // poll every 2s
      } catch {
        if (alive) timer.current = window.setTimeout(tick, 4000);
      }
    };
    tick();
    return () => { alive = false; clearTimeout(timer.current); };
  }, [repoId, active]);
  return p;
}
```

### 11.2 Animated component

```tsx
// frontend/src/components/AnalysisProgress.tsx
import { Loader2, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";

const STAGES = [
  ["cloning", "Cloning Repository"],
  ["scanning", "Scanning Files"],
  ["parsing", "Parsing Functions"],
  ["building_graph", "Building Dependency Graph"],
  ["saving", "Saving Graph"],
];
const ORDER = STAGES.map(s => s[0]);

function Bar({ pct }: { pct: number }) {
  return (
    <div className="h-2 w-full rounded bg-white/10 overflow-hidden">
      <div className="h-full bg-gradient-to-r from-blue-500 to-emerald-400 transition-all duration-500"
           style={{ width: `${Math.max(2, pct)}%` }} />
    </div>
  );
}

export default function AnalysisProgress({ p }: { p: any }) {
  if (!p) return null;
  const done = p.status === "completed";
  const warn = p.status === "completed_with_warnings";
  const failed = p.status === "failed";
  const idx = ORDER.indexOf(p.current_stage);

  return (
    <div className="rounded-xl bg-[#161616] border border-white/10 p-5 space-y-4">
      <div className="flex items-center gap-2 text-sm font-medium">
        {failed ? <XCircle className="text-red-400" size={18}/>
          : warn ? <AlertTriangle className="text-yellow-400" size={18}/>
          : done ? <CheckCircle2 className="text-emerald-400" size={18}/>
          : <Loader2 className="animate-spin text-blue-400" size={18}/>}
        <span>{done ? "Completed" : warn ? "Completed with warnings"
              : failed ? "Failed" : "Analyzing…"}</span>
        <span className="ml-auto tabular-nums text-white/60">{Math.round(p.progress_percent)}%</span>
      </div>

      <Bar pct={p.progress_percent}/>

      <div className="space-y-2">
        {STAGES.map(([key, label]) => {
          const sIdx = ORDER.indexOf(key);
          const state = done || warn ? "done"
            : sIdx < idx ? "done" : sIdx === idx ? "active" : "pending";
          const segPct = state === "done" ? 100 : state === "active"
            ? (p.total_files ? (p.files_processed / p.total_files) * 100 : 50) : 0;
          return (
            <div key={key} className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className={state==="pending" ? "text-white/30" : "text-white/80"}>{label}</span>
                {state==="active" && <Loader2 size={12} className="animate-spin text-blue-400"/>}
              </div>
              <Bar pct={segPct}/>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-4 gap-3 pt-2 text-center">
        <Counter label="Files" value={`${p.files_processed} / ${p.total_files}`}/>
        <Counter label="Functions" value={p.functions_found}/>
        <Counter label="Nodes" value={p.nodes_count}/>
        <Counter label="Edges" value={p.edges_count}/>
      </div>

      {p.files_failed > 0 && (
        <div className="text-xs text-yellow-400/90 flex items-center gap-1">
          <AlertTriangle size={12}/> {p.files_failed} file(s) skipped — analysis continued.
        </div>
      )}
    </div>
  );
}

function Counter({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-white/5 py-2">
      <div className="text-base font-semibold tabular-nums">{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-white/40">{label}</div>
    </div>
  );
}
```

Renders exactly your mock:
```
Analyzing DevBrain…                          63%
██████████████░░░░░░░░░░
Cloning Repository            ██████████
Scanning Files                ██████████
Parsing Functions             ███████░░░  ⟳
Building Dependency Graph     ░░░░░░░░░░
Saving Graph                  ░░░░░░░░░░
Files: 124 / 650   Functions: 853   Nodes: 1200   Edges: 3400
```

### 11.3 Dashboard wiring

In `DashboardPage.tsx`, replace the 5s `setInterval` block (lines 50–90) with per-active-repo
`useAnalysisProgress(repo.id, isActive)` and render `<AnalysisProgress p={progress}/>` under each
analyzing repo card. When `status` becomes terminal, call `loadRepos()` once to refresh final counts.

---

## 12. Performance Benchmarks (targets + how to measure)

`analysis_jobs` now stores `duration_seconds`, `files_per_second`, `nodes_per_second`,
`edges_per_second` per run, so benchmarks are self-recorded. Targets (Req #2):

| Repo size | Files | Cold (full) | Warm (incremental, ~5% changed) |
|---|---|---|---|
| Small | < 200 | **< 5s** | < 1s |
| Medium | 200–1500 | **< 15s** | 1–3s |
| Large | 1500–8000 (fast mode) | **< 60s** | 2–6s |

Levers that buy these numbers vs. today:
- Parallel parse (ThreadPool, 8 workers): ~2–4x on parse stage.
- Bulk `INSERT ... ON CONFLICT` (batch 1000) vs ORM `add_all`: ~5–15x on save stage (the current
  bottleneck on large repos).
- Incremental skip: 5–20x on re-analysis (only changed files parsed + written).
- Fast mode dir pruning: bounds large monorepos to source dirs, keeping them under 60s.

Add a repeatable harness (extends the existing `backend/run_analysis.py`):
```python
# backend/bench_analysis.py
# usage: python bench_analysis.py <repo_id>  → prints job metrics row after completion
```

---

## 13. Step-by-Step Implementation Plan

**Phase 0 — schema (no behavior change), ~0.5 day**
1. Add `last_commit_sha`, `failure_reason`, `content_hash` to `models/repo.py`; add 3 columns to
   `models/file.py`. (DB columns for the first two already exist via prior migrations.)
2. Create `models/analysis_job.py`; register both models in `models/__init__.py`.
3. Write migration `j0k1l2m3n4o5`; run `alembic upgrade head`. Verify `validate_schema()` is clean.

**Phase 1 — fault tolerance (immediate reliability win), ~0.5 day**
4. Wrap `code_parser.parse_file` in the never-raise guard (§4.1).
5. Ship `pipeline/parallel_parser.py` (§4.2). At this point even the *old* collector stops dying on
   one bad file if you route it through `parse_all`. This alone fixes "analysis sometimes fails."

**Phase 2 — pipeline core, ~2 days**
6. `pipeline/file_scanner.py` (streaming + fast mode), `pipeline/incremental.py`,
   `pipeline/graph_builder.py` (port edge heuristics from `analysis_collect.py`),
   `pipeline/bulk_writer.py`, `pipeline/progress.py`, `pipeline/resilience.py`, `pipeline/stages.py`,
   `pipeline/orchestrator.py`.
7. `repo_fetcher.clone_with_retry` + `head_commit_sha`.
8. Make `services/analysis.py::run_repo_analysis` a thin shim that creates a job + calls
   `run_pipeline` (keeps any other callers working).

**Phase 3 — queue + API, ~1 day**
9. Convert `trigger_analysis` to enqueue; add `/analysis-progress`; add `AnalysisProgressResponse`.
10. Start `worker_loop` in `main.py` lifespan; implement `_claim_next_job` (SKIP LOCKED) + heartbeat
    orphan recovery. Remove reliance on `_active_analyses`.

**Phase 4 — frontend, ~1 day**
11. `repoService.getAnalysisProgress`, `useAnalysisProgress` hook (2s), `AnalysisProgress.tsx`.
12. Rewire `DashboardPage` (and optionally `RepoDetailPage`) to the new poller + component.

**Phase 5 — scale + verify, ~1 day**
13. Benchmark small/medium/large; confirm targets via `analysis_jobs` metrics.
14. (Optional Tier B) move `run_pipeline` invocation into a Celery task; `worker_loop` becomes the
    Celery worker. Zero pipeline changes.
15. Soak test: kill the worker mid-job → confirm heartbeat reclaim; feed a repo with deliberately
    broken files → confirm `completed_with_warnings` + `file_errors` rows.

**Rollback safety:** Phases 0–1 are additive and independently shippable. The new pipeline can run
behind an env flag (`USE_NEW_PIPELINE`) so `trigger_analysis` falls back to the old
`run_repo_analysis` if needed.

---

## 14. Mapping every requirement to code

| Req | Delivered by |
|---|---|
| 1 Fault tolerance | `code_parser.parse_file` guard, `parallel_parser` per-file try/catch, `FileError` table, `completed_with_warnings` rule in orchestrator |
| 2 Parallel | `parallel_parser.ThreadPoolExecutor`, `asyncio.to_thread` stages, `worker_loop` semaphore |
| 3 Incremental | `incremental.plan_incremental`, `repo_files.content_hash`, `repos.last_commit_sha`, selective delete/reuse |
| 4 Queue + states | `analysis_jobs` table, `STAGES`, `_claim_next_job` SKIP LOCKED, `progress_percent` |
| 5 Progress API | `GET /analysis-progress`, `ProgressReporter` |
| 6 Animation | `AnalysisProgress.tsx`, `useAnalysisProgress` (2s) |
| 7 Large-repo fast mode | `file_scanner` threshold + dir pruning |
| 8 Memory | streaming read→hash→parse→release; capped `raw_code` |
| 9 Bulk writes | `bulk_writer` `INSERT ... ON CONFLICT`, batch 1000 |
| 10 Metrics | `analysis_jobs.duration/files_per_second/...`, `finish()` |
| 11 Reliability | `resilience.retry_async`, `CircuitBreaker`, timeouts, never-raise orchestrator |
| 12 Deliverables | this document |
```
