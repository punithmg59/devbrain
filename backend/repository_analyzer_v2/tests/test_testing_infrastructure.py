import pathlib
import pytest

from core.plugin_manager import PluginManager
from models import Repository, RepositoryFile
from pipeline import Pipeline, PipelineContext
from plugins.base import AnalyzerPlugin


def test_dummy_repo_dir_fixture(dummy_repo_dir: pathlib.Path):
    """Test that dummy_repo_dir fixture creates a valid temporary directory structure."""
    assert dummy_repo_dir.exists()
    assert dummy_repo_dir.is_dir()

    src_dir = dummy_repo_dir / "src"
    assert src_dir.exists()
    assert (src_dir / "main.py").exists()
    assert (src_dir / "utils.py").exists()
    assert (src_dir / "app.ts").exists()
    assert (dummy_repo_dir / "README.md").exists()


def test_dummy_repository_model_fixture(dummy_repository_model: Repository, dummy_repo_dir: pathlib.Path):
    """Test dummy_repository_model fixture."""
    assert dummy_repository_model.name == "dummy_sample_repo"
    assert dummy_repository_model.url == str(dummy_repo_dir)
    assert dummy_repository_model.branch == "main"


def test_mock_plugins_fixtures(mock_python_plugin, mock_ts_plugin):
    """Test mock plugins fixtures."""
    pm = PluginManager()
    pm.register(mock_python_plugin)
    pm.register(mock_ts_plugin)

    assert pm.get_by_language("python") is mock_python_plugin
    assert pm.get_by_language("typescript") is mock_ts_plugin

    file = RepositoryFile(path="src/main.py", name="main.py", extension="py")
    ast = mock_python_plugin.parse(file)
    assert ast == {"ast": "mock_ast_for_main.py"}

    symbols = mock_python_plugin.extract_symbols(file, ast)
    assert len(symbols) == 1
    assert symbols[0].name == "mock_function"


def test_pipeline_execution_with_fixtures(dummy_repository_model: Repository):
    """Test running full pipeline with dummy_repository_model fixture."""
    ctx = PipelineContext(run_id="infra-test-run", repository=dummy_repository_model)
    pipeline = Pipeline()
    res = pipeline.run(ctx)

    assert res.repository.id == dummy_repository_model.id
    assert res.status.value == "completed"
    assert len(res.metrics) == 8
