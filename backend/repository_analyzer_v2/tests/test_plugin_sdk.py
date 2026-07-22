import pytest
from pydantic import ValidationError
from typing import Any, List

from models import Edge, Import, Node, RepositoryFile, Symbol
from plugins.base import AnalyzerPlugin, PluginMetadata


class DummyPlugin(AnalyzerPlugin):
    """A concrete dummy plugin for testing the SDK base class."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="DummyAnalyzer",
            version="1.0.0",
            description="A dummy analyzer for testing",
            capabilities=["symbols", "imports"]
        )
        
    def initialize(self, config: Any) -> None:
        pass
        
    def language(self) -> str:
        return "dummy"
        
    def supported_extensions(self) -> List[str]:
        return ["dummy", "dum"]
        
    def parse(self, file: RepositoryFile) -> Any:
        return {"type": "dummy_ast"}
        
    def extract_entities(self, file: RepositoryFile, ast: Any) -> List[Node]:
        return []
        
    def extract_symbols(self, file: RepositoryFile, ast: Any) -> List[Symbol]:
        return []
        
    def extract_imports(self, file: RepositoryFile, ast: Any) -> List[Import]:
        return []
        
    def extract_calls(self, file: RepositoryFile, ast: Any) -> List[Edge]:
        return []
        
    def extract_routes(self, file: RepositoryFile, ast: Any) -> List[Any]:
        return []
        
    def cleanup(self) -> None:
        pass


def test_plugin_metadata_validation():
    """Test that PluginMetadata enforces semantic versioning."""
    with pytest.raises(ValidationError):
        PluginMetadata(
            name="BadPlugin",
            version="v1",  # Invalid format
            description="Test"
        )
        
    meta = PluginMetadata(
        name="GoodPlugin",
        version="1.2.3",
        description="Test"
    )
    assert meta.version == "1.2.3"


def test_dummy_plugin_implementation():
    """Test that our DummyPlugin successfully implements the abstract methods."""
    plugin = DummyPlugin()
    
    assert plugin.language() == "dummy"
    assert "dum" in plugin.supported_extensions()
    
    meta = plugin.metadata
    assert meta.name == "DummyAnalyzer"
    assert "symbols" in meta.capabilities
    
    file = RepositoryFile(path="test.dummy", name="test.dummy", extension="dummy")
    ast = plugin.parse(file)
    assert ast == {"type": "dummy_ast"}
    
    assert plugin.extract_symbols(file, ast) == []


def test_incomplete_plugin_fails():
    """Test that missing an abstract method fails instantiation."""
    class IncompletePlugin(AnalyzerPlugin):
        pass

    with pytest.raises(TypeError) as exc:
        IncompletePlugin()
        
    assert "Can't instantiate abstract class" in str(exc.value)
