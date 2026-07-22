import threading
from typing import Any, List

import pytest

from core.plugin_manager import PluginError, PluginManager
from models import Edge, Import, Node, RepositoryFile, Symbol
from plugins.base import AnalyzerPlugin, PluginMetadata


class TestPluginA(AnalyzerPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="PluginA", version="1.0.0", description="A")
        
    def initialize(self, config: Any) -> None: pass
    def language(self) -> str: return "python"
    def supported_extensions(self) -> List[str]: return ["py"]
    def parse(self, file: RepositoryFile) -> Any: return None
    def extract_entities(self, file: RepositoryFile, ast: Any) -> List[Node]: return []
    def extract_symbols(self, file: RepositoryFile, ast: Any) -> List[Symbol]: return []
    def extract_imports(self, file: RepositoryFile, ast: Any) -> List[Import]: return []
    def extract_calls(self, file: RepositoryFile, ast: Any) -> List[Edge]: return []
    def extract_routes(self, file: RepositoryFile, ast: Any) -> List[Any]: return []
    def cleanup(self) -> None: pass


class TestPluginB(AnalyzerPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="PluginB", version="1.0.0", description="B")
        
    def initialize(self, config: Any) -> None: pass
    def language(self) -> str: return "typescript"
    def supported_extensions(self) -> List[str]: return ["ts", "tsx"]
    def parse(self, file: RepositoryFile) -> Any: return None
    def extract_entities(self, file: RepositoryFile, ast: Any) -> List[Node]: return []
    def extract_symbols(self, file: RepositoryFile, ast: Any) -> List[Symbol]: return []
    def extract_imports(self, file: RepositoryFile, ast: Any) -> List[Import]: return []
    def extract_calls(self, file: RepositoryFile, ast: Any) -> List[Edge]: return []
    def extract_routes(self, file: RepositoryFile, ast: Any) -> List[Any]: return []
    def cleanup(self) -> None: pass


@pytest.fixture(autouse=True)
def reset_plugin_manager():
    """Reset the singleton state before each test."""
    PluginManager._instance = None
    manager = PluginManager()
    yield manager
    PluginManager._instance = None


def test_singleton_behavior(reset_plugin_manager):
    """Test that PluginManager acts as a singleton."""
    manager1 = PluginManager()
    manager2 = PluginManager()
    assert manager1 is manager2


def test_register_and_retrieve(reset_plugin_manager):
    """Test standard plugin registration and retrieval."""
    plugin_a = TestPluginA()
    reset_plugin_manager.register(plugin_a)
    
    assert reset_plugin_manager.get_by_language("python") is plugin_a
    assert reset_plugin_manager.get_by_extension("py") is plugin_a
    assert reset_plugin_manager.get_by_extension(".py") is plugin_a  # Should handle dots
    
    plugins = reset_plugin_manager.get_all()
    assert "PluginA" in plugins


def test_duplicate_registration_fails(reset_plugin_manager):
    """Test that registering a duplicate plugin or language throws PluginError."""
    plugin_a = TestPluginA()
    reset_plugin_manager.register(plugin_a)
    
    with pytest.raises(PluginError, match="is already registered"):
        reset_plugin_manager.register(plugin_a)


def test_unregister(reset_plugin_manager):
    """Test unregistering a plugin cleans up mappings."""
    plugin_b = TestPluginB()
    reset_plugin_manager.register(plugin_b)
    
    assert reset_plugin_manager.get_by_language("typescript") is not None
    
    reset_plugin_manager.unregister("PluginB")
    
    assert reset_plugin_manager.get_by_language("typescript") is None
    assert reset_plugin_manager.get_by_extension("ts") is None
    assert "PluginB" not in reset_plugin_manager.get_all()


def test_thread_safety_registration():
    """Test that multiple threads can register plugins safely without corrupting state."""
    PluginManager._instance = None
    manager = PluginManager()
    
    def register_worker(name, lang, ext):
        class ThreadPlugin(AnalyzerPlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(name=name, version="1.0.0", description=name)
            def initialize(self, config: Any) -> None: pass
            def language(self) -> str: return lang
            def supported_extensions(self) -> List[str]: return [ext]
            def parse(self, file: RepositoryFile) -> Any: return None
            def extract_entities(self, file: RepositoryFile, ast: Any) -> List[Node]: return []
            def extract_symbols(self, file: RepositoryFile, ast: Any) -> List[Symbol]: return []
            def extract_imports(self, file: RepositoryFile, ast: Any) -> List[Import]: return []
            def extract_calls(self, file: RepositoryFile, ast: Any) -> List[Edge]: return []
            def extract_routes(self, file: RepositoryFile, ast: Any) -> List[Any]: return []
            def cleanup(self) -> None: pass
            
        manager.register(ThreadPlugin())

    threads = []
    for i in range(10):
        t = threading.Thread(target=register_worker, args=(f"Plugin{i}", f"lang{i}", f"ext{i}"))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    assert len(manager.get_all()) == 10
    assert manager.get_by_language("lang5") is not None
