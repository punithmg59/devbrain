import concurrent.futures as cf
import logging
import os
from dataclasses import dataclass, field
from typing import Callable

from app.services.code_parser import parse_file

logger = logging.getLogger(__name__)

DEFAULT_WORKERS = min(8, (os.cpu_count() or 4))


@dataclass
class ParseResult:
    """
    parsed: dict mapping rel_path -> list of node dicts
            Only contains files that returned at least one node.
    errors: list of dicts, one per failed file.
            Each dict has keys: file_path, error_type, message
            These become FileError rows in the database.
    files_processed: total files attempted (success + failure)
    """
    parsed: dict[str, list[dict]] = field(default_factory=dict)
    errors: list[dict] = field(default_factory=list)
    files_processed: int = 0


def _parse_one(
    rel_path: str,
    content: str
) -> tuple[str, list[dict], dict | None]:
    """
    Parse a single file. NEVER raises — all exceptions are caught here.
    Returns (rel_path, nodes, error_dict_or_None).
    error_dict keys: file_path, error_type, message
    """
    try:
        nodes = parse_file(content, rel_path)
        return rel_path, nodes, None
    except Exception as exc:
        # Defense in depth: parse_file already swallows exceptions,
        # but if it somehow raises, we catch it here too.
        err = {
            "file_path": rel_path,
            "error_type": type(exc).__name__,
            "message": str(exc)[:500],
        }
        logger.warning("parallel_parser: exception escaped parse_file for %s: %s",
                       rel_path, exc)
        return rel_path, [], err


def parse_all(
    files: list[tuple[str, str]],
    *,
    max_workers: int = DEFAULT_WORKERS,
    on_progress: Callable[[int], None] | None = None,
) -> ParseResult:
    """
    Parse a list of (rel_path, content) tuples in parallel using threads.

    Args:
        files:        List of (relative_file_path, file_content) tuples.
        max_workers:  Thread pool size. Default is min(8, cpu_count).
        on_progress:  Optional callback called with (files_done_so_far: int)
                      every 25 files. Use this to update progress in the DB.

    Returns:
        ParseResult with .parsed dict, .errors list, .files_processed count.

    Thread safety:
        parse_file is stateless and safe to call from multiple threads.
        ParseResult is built in the main thread only — no shared mutation.

    Why threads not processes:
        ast.parse is a C extension that releases the GIL partially.
        The workload is mixed I/O (content already in memory but string
        ops) + C-level AST parsing. Threads give 2-4x speedup without
        the serialization overhead of ProcessPoolExecutor.
    """
    result = ParseResult()
    done_count = 0

    with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(_parse_one, rel_path, content): rel_path
            for rel_path, content in files
        }

        for future in cf.as_completed(future_to_path):
            rel_path, nodes, error = future.result()  # never raises

            if nodes:
                result.parsed[rel_path] = nodes
            if error:
                result.errors.append(error)

            done_count += 1
            result.files_processed = done_count

            if on_progress and done_count % 25 == 0:
                on_progress(done_count)

    # Final progress call so caller knows we finished
    if on_progress:
        on_progress(done_count)

    return result
