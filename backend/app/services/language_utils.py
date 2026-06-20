import os
from pathlib import Path

SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "vendor",
}

EXTENSION_LANGUAGE = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".vue": "Vue",
    ".sql": "SQL",
    ".md": "Markdown",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
}

ANALYZABLE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}

# Files that must never be decoded, previewed, or parsed. Storing their bytes
# (or a NUL-containing decode) into a Postgres text column raises
# CharacterNotInRepertoireError (0x00 invalid for UTF8).
BINARY_EXTENSIONS = {
    ".pkl", ".pt", ".pth", ".bin", ".exe", ".dll", ".so", ".jar",
    ".zip", ".tar", ".gz", ".pdf", ".png", ".jpg", ".jpeg", ".gif",
    ".mp4", ".mp3",
}

# Leading bytes sniffed for a NUL when classifying by content.
_BINARY_SNIFF_BYTES = 8192

MAX_FILE_BYTES = 512_000
MAX_FILES = 500
MAX_EDGES = 2500


def should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".")


def detect_language(path: str) -> str | None:
    return EXTENSION_LANGUAGE.get(Path(path).suffix.lower())


def is_analyzable(path: str) -> bool:
    return Path(path).suffix.lower() in ANALYZABLE_EXTENSIONS


def is_binary_file(path: str, raw: bytes | None = None) -> bool:
    """Return True if a file must be treated as binary (never decoded/parsed).

    Detection is by extension first, then by a NUL-byte sniff of the raw bytes.
    NUL (0x00) is valid UTF-8 but cannot be stored in a Postgres text column, so
    any file containing one is treated as binary regardless of its extension.
    """
    if Path(path).suffix.lower() in BINARY_EXTENSIONS:
        return True
    if raw is not None and b"\x00" in raw[:_BINARY_SNIFF_BYTES]:
        return True
    return False


def normalize_folder_path(folder_path: str) -> str:
    return folder_path.replace("\\", "/").strip("/")


def folder_depth(folder_path: str) -> int:
    if not folder_path:
        return 0
    return len(normalize_folder_path(folder_path).split("/"))


def iter_repo_files(root: str):
    """Yield relative file paths under root, skipping ignored dirs."""
    root_path = Path(root)
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
        for filename in filenames:
            if count >= MAX_FILES:
                return
            full = Path(dirpath) / filename
            rel = full.relative_to(root_path).as_posix()
            if should_skip_dir(Path(rel).parts[0]) if Path(rel).parts else False:
                continue
            try:
                size = full.stat().st_size
            except OSError:
                continue
            if size > MAX_FILE_BYTES:
                continue
            count += 1
            yield rel, full, size
