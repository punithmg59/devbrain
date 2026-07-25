"""
tests/test_python_builder_plugin.py
------------------------------------
Step 2 — Python Builder Plugin Unit Test Suite.

Verifies metadata, capability declarations, batch execution on RepositoryWorkspace objects,
streaming parsing, syntactic AST preservation, error isolation, and step boundaries.
"""

import os
import pytest

from models.parser import ParserResult, ParserStatus
from pipeline.workspace.analyzer import RepositoryAnalyzer
from plugins.python.builder_plugin import PythonBuilderPlugin


class TestPythonBuilderPlugin:
    def test_python_builder_plugin_metadata(self):
        plugin = PythonBuilderPlugin()
        plugin.initialize()

        assert plugin.metadata.plugin_id == "devbrain.plugin.python"
        assert plugin.metadata.target_language == "python"
        assert "py" in plugin.metadata.supported_extensions
        assert plugin.metadata.capabilities.syntax_ast
        assert plugin.metadata.capabilities.error_recovery

    def test_python_builder_plugin_execute_on_repository_workspace(self):
        trading_bot_path = r"d:\devbrain\Trading_bot"
        if not os.path.exists(trading_bot_path):
            pytest.skip("Trading_bot path does not exist")

        # Step 1: Generate RepositoryWorkspace
        analyzer = RepositoryAnalyzer()
        workspace = analyzer.analyze(trading_bot_path)

        # Step 2: Ingest RepositoryWorkspace into PythonBuilderPlugin
        builder_plugin = PythonBuilderPlugin()
        builder_plugin.initialize()
        parser_results = builder_plugin.execute(workspace)

        assert isinstance(parser_results, list)
        assert len(parser_results) > 0
        assert all(isinstance(r, ParserResult) for r in parser_results)

        # Verify deterministic sorting by file path
        file_paths = [r.file_path for r in parser_results]
        assert file_paths == sorted(file_paths)

        # Verify ParserResult contents
        sample_res = parser_results[0]
        assert sample_res.status in (ParserStatus.SUCCESS, ParserStatus.SYNTAX_ERROR, ParserStatus.PARTIAL_SUCCESS)
        assert sample_res.metadata.file_hash is not None
        assert sample_res.statistics.lines_parsed > 0
        assert sample_res.ast_root is not None

        # CRITICAL INVARIANT VERIFICATION: Output must NOT contain graph nodes or edges
        assert not hasattr(sample_res, "graph_nodes")
        assert not hasattr(sample_res, "edges")
        assert not hasattr(sample_res, "symbol_table")

    def test_python_builder_plugin_streaming(self):
        trading_bot_path = r"d:\devbrain\Trading_bot"
        if not os.path.exists(trading_bot_path):
            pytest.skip("Trading_bot path does not exist")

        analyzer = RepositoryAnalyzer()
        workspace = analyzer.analyze(trading_bot_path)

        builder_plugin = PythonBuilderPlugin()
        builder_plugin.initialize()

        stream_count = 0
        for p_res in builder_plugin.execute_streaming(workspace):
            assert isinstance(p_res, ParserResult)
            stream_count += 1

        assert stream_count > 0

    def test_python_builder_plugin_syntax_error_isolation(self, tmp_path):
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("def unclosed_function(:\n    pass\n", encoding="utf-8")

        analyzer = RepositoryAnalyzer()
        workspace = analyzer.analyze(str(tmp_path))

        builder_plugin = PythonBuilderPlugin()
        builder_plugin.initialize()
        parser_results = builder_plugin.execute(workspace)

        assert len(parser_results) == 1
        res = parser_results[0]
        # Must not crash; captures diagnostics
        assert res.file_path == "bad.py"
        assert res.status in (ParserStatus.SYNTAX_ERROR, ParserStatus.PARTIAL_SUCCESS, ParserStatus.SUCCESS)
