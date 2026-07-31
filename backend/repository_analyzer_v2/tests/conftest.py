import os
import sys
import pathlib

_pkg_root = pathlib.Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from typing import Any, List
import pytest
import pytest_asyncio

from core.events import EventBus
from core.plugin_manager import PluginManager
from models import Edge, Import, Node, Repository, RepositoryFile, Symbol
from plugins.base import AnalyzerPlugin, PluginMetadata
from utils.metrics import MetricsCollector


class MockLanguagePlugin(AnalyzerPlugin):
    """Configurable mock plugin for testing."""
    def __init__(
        self,
        name: str = "MockPythonPlugin",
        lang: str = "python",
        exts: List[str] = None,
        version: str = "1.0.0",
        capabilities: List[str] = None,
    ):
        self._name = name
        self._lang = lang
        self._exts = exts or ["py"]
        self._version = version
        self._capabilities = capabilities or ["symbols", "imports", "calls"]
        self.initialized = False
        self.cleaned_up = False

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self._name,
            version=self._version,
            description=f"Mock plugin for {self._lang}",
            capabilities=self._capabilities,
        )

    def initialize(self, config: Any) -> None:
        self.initialized = True

    def language(self) -> str:
        return self._lang

    def supported_extensions(self) -> List[str]:
        return self._exts

    def parse(self, file: RepositoryFile) -> Any:
        return {"ast": f"mock_ast_for_{file.name}"}

    def extract_entities(self, file: RepositoryFile, ast: Any) -> List[Node]:
        return [Node(id=f"node-{file.name}", type="file", name=file.name, file_path=file.path)]

    def extract_symbols(self, file: RepositoryFile, ast: Any) -> List[Symbol]:
        return [Symbol(name="mock_function", kind="function", line_number=1)]

    def extract_imports(self, file: RepositoryFile, ast: Any) -> List[Import]:
        return [Import(source="os", module="os", line_number=1)]

    def extract_calls(self, file: RepositoryFile, ast: Any) -> List[Edge]:
        return []

    def extract_routes(self, file: RepositoryFile, ast: Any) -> List[Any]:
        return []

    def cleanup(self) -> None:
        self.cleaned_up = True


@pytest.fixture
def mock_python_plugin() -> MockLanguagePlugin:
    """Fixture providing a mock Python analyzer plugin."""
    return MockLanguagePlugin(name="MockPythonPlugin", lang="python", exts=["py"])


@pytest.fixture
def mock_ts_plugin() -> MockLanguagePlugin:
    """Fixture providing a mock TypeScript analyzer plugin."""
    return MockLanguagePlugin(name="MockTSPlugin", lang="typescript", exts=["ts", "tsx"])


@pytest.fixture
def dummy_repo_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    """
    Fixture creating a dummy repository directory structure with sample source files.
    """
    repo_dir = tmp_path / "dummy_sample_repo"
    repo_dir.mkdir()

    # Create subdirectories
    src_dir = repo_dir / "src"
    src_dir.mkdir()
    tests_dir = repo_dir / "tests"
    tests_dir.mkdir()

    # Create sample Python file
    main_py = src_dir / "main.py"
    main_py.write_text("import os\n\ndef main():\n    print('Hello World')\n")

    # Create sample Utils Python file
    utils_py = src_dir / "utils.py"
    utils_py.write_text("def helper():\n    return 42\n")

    # Create sample TypeScript file
    app_ts = src_dir / "app.ts"
    app_ts.write_text("export const run = (): void => { console.log('TS App'); };\n")

    # Create README file
    readme = repo_dir / "README.md"
    readme.write_text("# Dummy Sample Repo\n")

    return repo_dir


@pytest.fixture
def dummy_repository_model(dummy_repo_dir: pathlib.Path) -> Repository:
    """Fixture providing a Repository Pydantic model pointing to dummy_repo_dir."""
    return Repository(
        id="dummy-repo-001",
        url=str(dummy_repo_dir),
        name="dummy_sample_repo",
        branch="main",
    )


@pytest.fixture(autouse=True)
def reset_singletons(monkeypatch):
    """Autouse fixture resetting singleton instances and environment before each test."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/devbrain_test")
    from config.settings import get_settings
    get_settings.cache_clear()

    PluginManager._instance = None
    EventBus._instance = None
    MetricsCollector._instance = None
    yield
    PluginManager._instance = None
    EventBus._instance = None
    MetricsCollector._instance = None
    get_settings.cache_clear()
