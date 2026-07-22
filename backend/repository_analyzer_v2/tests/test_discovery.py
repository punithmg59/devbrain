import os
import pathlib
import pytest

from models import (
    DiscoveryConfig,
    Language,
    Repository,
    RepositoryFile,
    RepositorySummary,
)
from pipeline.context import PipelineContext
from pipeline.discovery import (
    DiscoveryStage,
    RepositoryDiscovery,
    RepositoryValidator,
)
from pipeline.pipeline import Pipeline
from utils.exceptions import ErrorCode, RepositoryError
from utils.ignore_system import IgnoreSystem
from utils.language_detector import LanguageDetector


# ---------------------------------------------------------------------------
# RepositoryValidator Tests
# ---------------------------------------------------------------------------

def test_validator_nonexistent_path():
    """Test validator raises RepositoryError for missing path."""
    with pytest.raises(RepositoryError) as exc_info:
        RepositoryValidator.validate("/path/does/not/exist/999")
    assert exc_info.value.code == ErrorCode.REPO_NOT_FOUND


def test_validator_file_instead_of_directory(tmp_path: pathlib.Path):
    """Test validator raises RepositoryError when path is a file, not a dir."""
    file_path = tmp_path / "single_file.txt"
    file_path.write_text("hello")
    with pytest.raises(RepositoryError) as exc_info:
        RepositoryValidator.validate(file_path)
    assert exc_info.value.code == ErrorCode.REPO_NOT_FOUND


def test_validator_bare_folder_vs_git(tmp_path: pathlib.Path):
    """Test validator detects git repo vs bare folder."""
    # Bare folder
    path, is_git, is_empty = RepositoryValidator.validate(tmp_path)
    assert is_git is False

    # Create .git folder
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    path, is_git, is_empty = RepositoryValidator.validate(tmp_path)
    assert is_git is True


def test_validator_empty_repository(tmp_path: pathlib.Path):
    """Test validator detects empty repository."""
    path, is_git, is_empty = RepositoryValidator.validate(tmp_path)
    assert is_empty is True

    # Add a file
    (tmp_path / "app.py").write_text("print('hi')")
    path, is_git, is_empty = RepositoryValidator.validate(tmp_path)
    assert is_empty is False


# ---------------------------------------------------------------------------
# LanguageDetector Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path_str,expected_lang", [
    ("main.py", Language.PYTHON),
    ("utils.pyi", Language.PYTHON),
    ("index.ts", Language.TYPESCRIPT),
    ("component.tsx", Language.TYPESCRIPT),
    ("app.js", Language.JAVASCRIPT),
    ("App.jsx", Language.JAVASCRIPT),
    ("Main.java", Language.JAVA),
    ("server.go", Language.GO),
    ("Program.cs", Language.CSHARP),
    ("data.txt", Language.UNKNOWN),
    ("binary_file", Language.UNKNOWN),
])
def test_language_detector(path_str, expected_lang):
    """Test LanguageDetector maps extensions correctly."""
    assert LanguageDetector.detect(path_str) == expected_lang


# ---------------------------------------------------------------------------
# IgnoreSystem Tests
# ---------------------------------------------------------------------------

def test_ignore_system_builtins(tmp_path: pathlib.Path):
    """Test IgnoreSystem filters built-in ignored files and directories."""
    ignore = IgnoreSystem(tmp_path)

    assert ignore.should_ignore(tmp_path / ".git") is True
    assert ignore.should_ignore(tmp_path / "node_modules" / "package.json") is True
    assert ignore.should_ignore(tmp_path / "venv" / "bin" / "python") is True
    assert ignore.should_ignore(tmp_path / "__pycache__" / "main.cpython-311.pyc") is True
    assert ignore.should_ignore(tmp_path / "src" / "main.py") is False


def test_ignore_system_gitignore_and_custom(tmp_path: pathlib.Path):
    """Test IgnoreSystem parses .gitignore and custom patterns."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.log\ntemp/\n")

    ignore = IgnoreSystem(tmp_path, custom_patterns=["*.tmp"])

    assert ignore.should_ignore(tmp_path / "app.log") is True
    assert ignore.should_ignore(tmp_path / "temp" / "data.json") is True
    assert ignore.should_ignore(tmp_path / "file.tmp") is True
    assert ignore.should_ignore(tmp_path / "app.py") is False


# ---------------------------------------------------------------------------
# RepositoryDiscovery Scan & Metadata Tests
# ---------------------------------------------------------------------------

def test_discovery_empty_repo(tmp_path: pathlib.Path):
    """Test discover() returns empty list for empty repository."""
    discovery = RepositoryDiscovery()
    files = discovery.discover(tmp_path)
    assert files == []


def test_discovery_small_repo(dummy_repo_dir: pathlib.Path):
    """Test discover() scans files, detects languages, and computes metadata."""
    discovery = RepositoryDiscovery()
    files = discovery.discover(dummy_repo_dir)

    assert len(files) >= 4
    rel_paths = {f.path for f in files}

    assert "src/main.py" in rel_paths
    assert "src/utils.py" in rel_paths
    assert "src/app.ts" in rel_paths
    assert "README.md" in rel_paths

    main_f = next(f for f in files if f.path == "src/main.py")
    assert main_f.language == "python"
    assert main_f.extension == "py"
    assert main_f.hash_sha256 is not None
    assert main_f.line_count > 0
    assert main_f.status == "discovered"


def test_discover_single_file(dummy_repo_dir: pathlib.Path):
    """Test discover_file() on a single target file."""
    discovery = RepositoryDiscovery()
    target_path = dummy_repo_dir / "src" / "main.py"

    f = discovery.discover_file(target_path, dummy_repo_dir)
    assert f is not None
    assert f.path == "src/main.py"
    assert f.language == "python"

    # Ignored file check
    ignored_path = dummy_repo_dir / ".git" / "HEAD"
    assert discovery.discover_file(ignored_path, dummy_repo_dir) is None


def test_summarize_repository(dummy_repo_dir: pathlib.Path):
    """Test summarize() calculates summary metrics."""
    discovery = RepositoryDiscovery()
    files = discovery.discover(dummy_repo_dir)
    summary = discovery.summarize(files, dummy_repo_dir)

    assert isinstance(summary, RepositorySummary)
    assert summary.total_files == len(files)
    assert summary.total_folders >= 1
    assert summary.language_distribution.get("python") == 2
    assert summary.language_distribution.get("typescript") == 1
    assert summary.total_size_bytes > 0
    assert summary.largest_file is not None


def test_discovery_oversized_file(tmp_path: pathlib.Path):
    """Test discovery flags oversized files without breaking scan."""
    large_file = tmp_path / "large.py"
    # Create 20KB file
    large_file.write_bytes(b"x = 1\n" * 4000)

    discovery = RepositoryDiscovery()
    # Limit max size to 5KB
    cfg = DiscoveryConfig(max_file_size_kb=5)
    files = discovery.discover(tmp_path, config=cfg)

    assert len(files) == 1
    f = files[0]
    assert f.status == "too_large"
    assert f.hash_sha256 is None


# ---------------------------------------------------------------------------
# Integration with Pipeline & DiscoveryStage
# ---------------------------------------------------------------------------

def test_pipeline_integration_with_discovery(dummy_repository_model: Repository):
    """Test full pipeline run populates discovered_files and repository_summary in context."""
    ctx = PipelineContext(run_id="disc-pipeline-test", repository=dummy_repository_model)
    pipeline = Pipeline()
    res_ctx = pipeline.run(ctx)

    assert "discovered_files" in res_ctx.metadata
    assert "repository_summary" in res_ctx.metadata

    files = res_ctx.metadata["discovered_files"]
    assert len(files) >= 4
    assert res_ctx.progress.total_files == len(files)
