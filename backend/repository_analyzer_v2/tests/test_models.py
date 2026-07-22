from datetime import datetime
from pydantic import ValidationError
import pytest

from models import (
    AnalysisResult,
    AnalysisRun,
    Edge,
    Export,
    Folder,
    Import,
    Node,
    PipelineStage,
    Repository,
    RepositoryFile,
    Symbol,
)


def test_repository_file_extension_validation():
    """Test that extensions starting with '.' are cleaned up."""
    file = RepositoryFile(
        path="src/main.py",
        name="main.py",
        extension=".py",
        size_bytes=1024
    )
    assert file.extension == "py"
    
    file_no_dot = RepositoryFile(
        path="src/utils.js",
        name="utils.js",
        extension="js",
        size_bytes=500
    )
    assert file_no_dot.extension == "js"


def test_repository_file_size_validation():
    """Test that size_bytes must be >= 0."""
    with pytest.raises(ValidationError):
        RepositoryFile(
            path="src/main.py",
            name="main.py",
            extension="py",
            size_bytes=-10
        )


def test_repository_defaults():
    """Test default values in Repository model."""
    repo = Repository(
        id="repo-123",
        url="https://github.com/punithmg59/Trading_bot",
        name="Trading_bot"
    )
    assert repo.branch == "main"
    assert repo.commit_hash is None
    assert isinstance(repo.created_at, datetime)


def test_graph_node_and_edge():
    """Test creating nodes and edges for the graph."""
    sym = Symbol(name="calculate_sum", kind="function", line_number=10)
    imp = Import(source="math", module=None, line_number=1)
    exp = Export(name="calculate_sum", line_number=10)
    
    node = Node(
        id="node-1",
        type="file",
        name="math_utils.py",
        file_path="src/math_utils.py",
        symbols=[sym],
        imports=[imp],
        exports=[exp],
        metadata={"complexity": 5}
    )
    
    assert node.id == "node-1"
    assert len(node.symbols) == 1
    assert node.symbols[0].name == "calculate_sum"
    
    edge = Edge(
        source_id="node-1",
        target_id="node-2",
        type="imports",
        metadata={"weight": 1}
    )
    assert edge.source_id == "node-1"
    assert edge.type == "imports"


def test_analysis_run_and_result():
    """Test pipeline run models and enums."""
    result = AnalysisResult(
        repository_id="repo-123",
        total_files_analyzed=100,
        total_nodes=150,
        total_edges=200,
        errors=["File timeout in slow_file.py"]
    )
    
    run = AnalysisRun(
        id="run-456",
        repository_id="repo-123",
        status="completed",
        current_stage=PipelineStage.REPORTING,
        result=result
    )
    
    assert run.current_stage == PipelineStage.REPORTING
    assert run.result is not None
    assert run.result.total_nodes == 150
    assert run.result.repository_id == "repo-123"


def test_analysis_result_validation():
    """Test negative values fail validation."""
    with pytest.raises(ValidationError):
        AnalysisResult(
            repository_id="repo-123",
            total_files_analyzed=-5
        )
