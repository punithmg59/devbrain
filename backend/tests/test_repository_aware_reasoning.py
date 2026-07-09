"""
Test suite for repository-aware AI reasoning.

Tests that all AI responses are grounded in repository data:
- AST information
- Dependency graph
- Call graph
- Classes
- Functions
- API routes
- Imports

Tests validation to prevent dependency fabrication.
Tests limitation statements for missing evidence.
"""

import pytest
from uuid import uuid4
from app.services.engineering_evidence.models import (
    EngineeringEvidence, ASTNode, DependencyGraph, DependencyEdge,
    CallGraph, ClassInfo, FunctionInfo, APIRoute, ImportInfo,
    Criticality, EvidenceCategory, EvidenceGroup
)
from app.services.engineering_evidence.repository_data_collector import RepositoryDataCollector


class TestRepositoryDataCollector:
    """Test repository data collection."""
    
    @pytest.fixture
    def collector(self):
        return RepositoryDataCollector()
    
    def test_collect_repository_data_structure(self, collector):
        """Test that collect_repository_data returns correct structure."""
        repo_id = uuid4()
        repo_path = "/test/repo"
        
        data = collector.collect_repository_data(
            repo_id=repo_id,
            repo_path=repo_path,
            db=None  # No DB for this test
        )
        
        # Check structure
        assert 'ast_nodes' in data
        assert 'dependency_graph' in data
        assert 'call_graph' in data
        assert 'classes' in data
        assert 'functions' in data
        assert 'api_routes' in data
        assert 'imports' in data
        
        # Check types
        assert isinstance(data['ast_nodes'], list)
        assert isinstance(data['classes'], list)
        assert isinstance(data['functions'], list)
        assert isinstance(data['api_routes'], list)
        assert isinstance(data['imports'], list)
    
    def test_build_dependency_graph(self, collector):
        """Test dependency graph building."""
        ast_nodes = [
            ASTNode(node_type="function", name="func1", file_path="test.py", line_number=1),
            ASTNode(node_type="function", name="func2", file_path="test.py", line_number=10),
        ]
        
        imports = [
            ImportInfo(module="os", file_path="test.py", line_number=1, import_type="direct_import"),
        ]
        
        graph = collector._build_dependency_graph(ast_nodes, imports)
        
        assert isinstance(graph, DependencyGraph)
        assert graph.total_nodes == 2
        assert graph.total_edges >= 1  # At least the import edge
    
    def test_build_call_graph(self, collector):
        """Test call graph building."""
        functions = [
            FunctionInfo(
                name="main",
                file_path="test.py",
                line_number=1,
                calls=["helper"]
            ),
            FunctionInfo(
                name="helper",
                file_path="test.py",
                line_number=10,
                calls=[]
            ),
        ]
        
        call_graph = collector._build_call_graph(functions)
        
        assert isinstance(call_graph, CallGraph)
        assert len(call_graph.function_calls) == 1
        assert call_graph.function_calls[0]['from'] == 'main'
        assert call_graph.function_calls[0]['to'] == 'helper'
    
    def test_validate_dependencies(self, collector):
        """Test dependency validation to prevent fabrication."""
        graph = DependencyGraph(
            nodes=["node1", "node2", "node3"],
            edges=[
                DependencyEdge(from_node="node1", to_node="node2", edge_type="calls", confidence=0.9),
                DependencyEdge(from_node="node1", to_node="unknown_node", edge_type="calls", confidence=0.9),
            ],
            total_nodes=3,
            total_edges=2
        )
        
        allowed_nodes = ["node1", "node2", "node3"]
        
        errors = collector.validate_dependencies(graph, allowed_nodes)
        
        # Should detect the unknown node
        assert len(errors) == 1
        assert "unknown_node" in errors[0]


class TestEngineeringEvidenceDataCompleteness:
    """Test data completeness calculations."""
    
    @pytest.fixture
    def evidence(self):
        return EngineeringEvidence(
            target_id=uuid4(),
            target_name="test",
            target_type="function",
            repo_id=uuid4(),
            overall_summary="Test summary"
        )
    
    def test_calculate_data_completeness_empty(self, evidence):
        """Test completeness calculation with empty data."""
        evidence.calculate_data_completeness()
        
        assert evidence.data_completeness['ast_nodes'] == 0.0
        assert evidence.data_completeness['dependency_graph'] == 0.0
        assert evidence.data_completeness['call_graph'] == 0.0
        assert evidence.data_completeness['classes'] == 0.0
        assert evidence.data_completeness['functions'] == 0.0
        assert evidence.data_completeness['api_routes'] == 0.0
        assert evidence.data_completeness['imports'] == 0.0
    
    def test_calculate_data_completeness_with_data(self, evidence):
        """Test completeness calculation with data."""
        evidence.ast_nodes = [
            ASTNode(node_type="function", name="func1", file_path="test.py", line_number=1)
        ]
        evidence.classes = [
            ClassInfo(name="TestClass", file_path="test.py", line_number=1)
        ]
        evidence.functions = [
            FunctionInfo(name="func1", file_path="test.py", line_number=1)
        ]
        
        evidence.calculate_data_completeness()
        
        assert evidence.data_completeness['ast_nodes'] > 0.0
        assert evidence.data_completeness['classes'] > 0.0
        assert evidence.data_completeness['functions'] > 0.0
    
    def test_generate_limitation_statements_empty(self, evidence):
        """Test limitation statement generation with empty data."""
        evidence.calculate_data_completeness()
        evidence.generate_limitation_statements()
        
        # Should have limitations for all empty data types
        assert len(evidence.limitations) > 0
        assert any("AST" in lim for lim in evidence.limitations)
        assert any("dependency" in lim.lower() for lim in evidence.limitations)
    
    def test_generate_limitation_statements_full(self, evidence):
        """Test limitation statement generation with full data."""
        # Add sufficient data to all fields
        evidence.ast_nodes = [ASTNode(node_type="function", name=f"func{i}", file_path="test.py", line_number=i) for i in range(10)]
        evidence.dependency_graph = DependencyGraph(
            nodes=["node1", "node2"],
            edges=[DependencyEdge(from_node="node1", to_node="node2", edge_type="calls", confidence=0.9)],
            total_nodes=2,
            total_edges=20
        )
        evidence.call_graph = CallGraph(function_calls=[{"from": "f1", "to": "f2"} for _ in range(10)])
        evidence.classes = [ClassInfo(name=f"Class{i}", file_path="test.py", line_number=i) for i in range(5)]
        evidence.functions = [FunctionInfo(name=f"func{i}", file_path="test.py", line_number=i) for i in range(20)]
        evidence.api_routes = [APIRoute(path=f"/api/{i}", method="GET", handler=f"handler{i}", file_path="test.py", line_number=i) for i in range(5)]
        evidence.imports = [ImportInfo(module=f"module{i}", file_path="test.py", line_number=i, import_type="direct_import") for i in range(10)]
        evidence.evidence_confidence = 0.8
        
        evidence.calculate_data_completeness()
        evidence.generate_limitation_statements()
        
        # Should have minimal limitations
        assert len(evidence.limitations) == 1
        assert "successfully" in evidence.limitations[0]


class TestRepositoryAwareReasoning:
    """Test that reasoning is grounded in repository data."""
    
    def test_evidence_contains_repository_data(self):
        """Test that EngineeringEvidence contains all required repository data types."""
        evidence = EngineeringEvidence(
            target_id=uuid4(),
            target_name="test",
            target_type="function",
            repo_id=uuid4(),
            overall_summary="Test summary",
            ast_nodes=[
                ASTNode(node_type="function", name="func1", file_path="test.py", line_number=1)
            ],
            dependency_graph=DependencyGraph(
                nodes=["node1"],
                edges=[],
                total_nodes=1,
                total_edges=0
            ),
            call_graph=CallGraph(function_calls=[]),
            classes=[
                ClassInfo(name="TestClass", file_path="test.py", line_number=1)
            ],
            functions=[
                FunctionInfo(name="func1", file_path="test.py", line_number=1)
            ],
            api_routes=[
                APIRoute(path="/api/test", method="GET", handler="handler", file_path="test.py", line_number=1)
            ],
            imports=[
                ImportInfo(module="os", file_path="test.py", line_number=1, import_type="direct_import")
            ]
        )
        
        # Verify all data types are present
        assert len(evidence.ast_nodes) > 0
        assert evidence.dependency_graph is not None
        assert evidence.call_graph is not None
        assert len(evidence.classes) > 0
        assert len(evidence.functions) > 0
        assert len(evidence.api_routes) > 0
        assert len(evidence.imports) > 0
    
    def test_missing_data_types_identified(self):
        """Test that missing data types are correctly identified."""
        evidence = EngineeringEvidence(
            target_id=uuid4(),
            target_name="test",
            target_type="function",
            repo_id=uuid4(),
            overall_summary="Test summary"
        )
        # No data added
        
        evidence.calculate_data_completeness()
        
        # All data types should be missing
        assert len(evidence.missing_data_types) > 0
        assert 'ast_nodes' in evidence.missing_data_types
        assert 'dependency_graph' in evidence.missing_data_types
        assert 'call_graph' in evidence.missing_data_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
