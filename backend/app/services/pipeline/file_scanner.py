import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from app.services.language_utils import (
    detect_language,
    ANALYZABLE_EXTENSIONS,
    SKIP_DIRS,
    MAX_FILE_BYTES,
)

logger = logging.getLogger(__name__)

# Directories that are never analyzed regardless of content.
# Extended from language_utils.SKIP_DIRS with additional common dirs.
_SKIP_DIRS = SKIP_DIRS | {
    "env", ".env", "out", "target", ".idea", ".vscode", ".cache",
    "eggs", ".eggs", "htmlcov", ".hypothesis",
}

# In fast mode, only descend into directories whose name matches
# one of these hints at the TOP level of the repository.
FAST_MODE_SOURCE_HINTS = {
    "src", "app", "lib", "api", "services", "models", "server",
    "backend", "core", "internal", "pkg", "routes", "controllers",
    "handlers", "db", "database", "domain", "modules", "features",
    "components", "utils", "helpers", "middleware", "workers",
}

# Files larger than this are skipped — they are almost always
# generated or minified and not useful for architecture analysis.
_SCANNER_MAX_FILE_BYTES = 500_000  # 500 KB

# If a repo has more than this many files after SKIP_DIRS pruning,
# activate fast mode automatically.
FAST_MODE_THRESHOLD = 3_000


@dataclass
class ScannedFile:
    rel_path: str         # relative path from repo root, e.g. "src/auth/service.py"
    abs_path: str         # absolute path on disk
    size_bytes: int       # file size in bytes
    language: str | None  # detected language, e.g. "python", "javascript", None
    is_analyzable: bool   # True if language is in ANALYZABLE_EXTENSIONS
    # Private attributes set by incremental.py
    _content: str | None = None
    content_hash: str | None = None


@dataclass
class ScanResult:
    files: list[ScannedFile]        # all files found (analyzable + non-analyzable)
    analyzable: list[ScannedFile]   # subset that will be parsed
    files_total: int                # len(files)
    analyzable_total: int           # len(analyzable)
    fast_mode: bool                 # True if fast mode was activated
    skipped_dirs: list[str]         # top-level dirs skipped in fast mode


def _should_skip_dir(dirname: str) -> bool:
    """
    Return True if a directory should be skipped entirely.
    Matches against SKIP_DIRS and hidden directories (start with dot).
    """
    return dirname in _SKIP_DIRS or dirname.startswith(".")


def _count_files_quick(root: str) -> int:
    """
    Fast approximate file count. Walks the tree respecting SKIP_DIRS.
    Stops counting early once count exceeds FAST_MODE_THRESHOLD * 2
    to avoid spending time counting a huge repo we already know is large.
    Returns the count (may be less than actual if early-stopped).
    """
    count = 0
    early_stop = FAST_MODE_THRESHOLD * 2
    
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter dirnames in-place to prevent descending into skipped dirs
        dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]
        
        count += len(filenames)
        if count >= early_stop:
            return count
    
    return count


def scan(clone_path: str) -> ScanResult:
    """
    Walk clone_path and return a ScanResult.

    Algorithm:
      1. Call _count_files_quick to decide if fast mode is needed.

      2. Walk the directory tree using os.walk with topdown=True.

      3. At each directory, filter dirnames in-place to remove
         entries in SKIP_DIRS and entries starting with ".".
         This prevents os.walk from descending into them.

      4. If fast_mode is True and we are at depth 1 (direct children
         of the repo root), additionally filter out any directory
         whose lowercase name is not in FAST_MODE_SOURCE_HINTS.
         Record skipped top-level dirs in skipped_dirs list.

      5. For each file:
         a. Skip if size > MAX_FILE_BYTES.
         b. Get relative path from clone_path root.
         c. Detect language using detect_language() from language_utils.
         d. Set is_analyzable based on whether language was detected
            AND the extension is in ANALYZABLE_EXTENSIONS.
         e. Append to files list.
         f. If is_analyzable, also append to analyzable list.

      6. Return ScanResult with all collected data and fast_mode flag.

    Memory contract:
      scan() does NOT read any file content.
      It only calls os.stat() (via os.walk) for size and os.path
      operations for paths. Peak memory is O(number of files) for
      the ScannedFile objects, not O(sum of file sizes).
    """
    files: list[ScannedFile] = []
    analyzable: list[ScannedFile] = []
    skipped_dirs: list[str] = []
    
    # Decide if fast mode is needed
    quick_count = _count_files_quick(clone_path)
    fast_mode = quick_count >= FAST_MODE_THRESHOLD
    
    root_path = Path(clone_path)
    
    for dirpath, dirnames, filenames in os.walk(clone_path, topdown=True):
        # Filter dirnames in-place to prevent descending into skipped dirs
        dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]
        
        # Calculate depth from root
        rel_dir = Path(dirpath).relative_to(root_path)
        depth = len(rel_dir.parts) if rel_dir.parts else 0
        
        # Fast mode: at depth 0 (root), skip non-source dirs
        if fast_mode and depth == 0:
            original_dirnames = list(dirnames)
            dirnames[:] = [d for d in dirnames if d.lower() in FAST_MODE_SOURCE_HINTS]
            skipped = set(original_dirnames) - set(dirnames)
            skipped_dirs.extend(skipped)
        
        for filename in filenames:
            try:
                full_path = Path(dirpath) / filename
                
                # Skip large files
                size = full_path.stat().st_size
                if size > _SCANNER_MAX_FILE_BYTES:
                    continue
                
                # Get relative path
                rel_path = full_path.relative_to(root_path).as_posix()
                
                # Detect language
                language = detect_language(rel_path)
                
                # Determine if analyzable
                is_analyzable = (
                    language is not None and
                    Path(rel_path).suffix.lower() in ANALYZABLE_EXTENSIONS
                )
                
                sf = ScannedFile(
                    rel_path=rel_path,
                    abs_path=str(full_path),
                    size_bytes=size,
                    language=language,
                    is_analyzable=is_analyzable,
                )
                
                files.append(sf)
                if is_analyzable:
                    analyzable.append(sf)
                    
            except (OSError, ValueError) as e:
                # Skip unreadable files or broken symlinks
                logger.debug("Skipping file due to error: %s", e)
                continue
    
    return ScanResult(
        files=files,
        analyzable=analyzable,
        files_total=len(files),
        analyzable_total=len(analyzable),
        fast_mode=fast_mode,
        skipped_dirs=skipped_dirs,
    )


def read_file_content(sf: ScannedFile) -> tuple[str, str]:
    """
    Read one file and return (content_string, sha256_hex).

    Reads bytes, computes SHA-256 hash of raw bytes,
    then decodes to string with UTF-8 errors='replace'.

    This is called per-file during analysis, never for all files
    at once, so memory usage stays bounded.

    Returns:
        (content, content_hash) tuple.
        content: decoded string, may contain replacement chars for non-UTF8.
        content_hash: lowercase hex SHA-256 of the raw bytes.
    """
    with open(sf.abs_path, 'rb') as f:
        raw_bytes = f.read()
    
    content_hash = hashlib.sha256(raw_bytes).hexdigest()
    content = raw_bytes.decode('utf-8', errors='replace')
    
    return content, content_hash
