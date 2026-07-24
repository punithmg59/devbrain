"""
tests/test_repository_workspace_pipeline.py
--------------------------------------------
Step 1 — Repository Workspace Pipeline Test Suite.

Verifies repository loader, validation, ignore rule evaluation, directory walker,
language & technology detector, builder plugin selector, and RepositoryWorkspace creation.
"""

import os
import pytest

from pipeline.workspace import (
    DirectoryWalker,
    IgnoreRuleEngine,
    LanguageDetector,
    PluginSelector,
    RepositoryAnalyzer,
    RepositoryLoader,
    RepositoryNotFoundError,
    RepositoryValidator,
    RepositoryWorkspace,
)


class TestRepositoryWorkspacePipeline:
    def test_ignore_rule_engine_defaults(self):
        engine = IgnoreRuleEngine()

        assert engine.is_ignored_directory(".git")
        assert engine.is_ignored_directory("node_modules")
        assert engine.is_ignored_directory("__pycache__")
        assert engine.is_ignored_directory("venv")
        assert not engine.is_ignored_directory("src")

        assert engine.is_ignored_file("app.pyc")
        assert engine.is_ignored_file("binary.exe")
        assert engine.is_ignored_file("image.png")
        assert not engine.is_ignored_file("main.py")

    def test_ignore_rule_engine_custom_rules(self):
        engine = IgnoreRuleEngine(custom_patterns=["*.log", "temp_*"])
        assert engine.is_ignored_file("error.log")
        assert engine.is_ignored_file("temp_file.txt")
        assert not engine.is_ignored_file("data.json")

    def test_language_detector_python(self, tmp_path):
        # Create dummy python project
        py_file = tmp_path / "main.py"
        py_file.write_text("print('hello')", encoding="utf-8")

        manifest = tmp_path / "pyproject.toml"
        manifest.write_text("[tool.poetry]\nname = 'test'\ndependencies = {fastapi = '^0.100.0'}", encoding="utf-8")

        analyzer = RepositoryAnalyzer()
        workspace = analyzer.analyze(str(tmp_path))

        assert len(workspace.detected_languages) >= 1
        assert workspace.detected_languages[0].name == "python"

        fw_names = [fw.name for fw in workspace.detected_frameworks]
        assert "FastAPI" in fw_names

    def test_language_detector_typescript(self, tmp_path):
        ts_file = tmp_path / "index.ts"
        ts_file.write_text("console.log('hi');", encoding="utf-8")

        pkg_json = tmp_path / "package.json"
        pkg_json.write_text('{"name": "test", "dependencies": {"react": "^18.0.0"}}', encoding="utf-8")

        analyzer = RepositoryAnalyzer()
        workspace = analyzer.analyze(str(tmp_path))

        lang_names = [l.name for l in workspace.detected_languages]
        assert "typescript" in lang_names

        fw_names = [fw.name for fw in workspace.detected_frameworks]
        assert "React" in fw_names

    def test_plugin_selector(self, tmp_path):
        (tmp_path / "app.py").write_text("import fastapi", encoding="utf-8")
        (tmp_path / "requirements.txt").write_text("fastapi>=0.95.0", encoding="utf-8")

        analyzer = RepositoryAnalyzer()
        workspace = analyzer.analyze(str(tmp_path))

        plugin_ids = [p.plugin_id for p in workspace.builder_plugins_required]
        assert "devbrain.plugin.python" in plugin_ids

    def test_repository_validator(self, tmp_path):
        validator = RepositoryValidator()

        # Valid non-empty directory
        (tmp_path / "dummy.txt").write_text("test", encoding="utf-8")
        report = validator.validate(str(tmp_path))
        assert report.is_valid
        assert report.error_count == 0

        # Non-existent directory
        report_missing = validator.validate(str(tmp_path / "missing_dir"))
        assert not report_missing.is_valid
        assert report_missing.error_count == 1

    def test_analyzer_end_to_end_on_trading_bot(self):
        trading_bot_path = r"d:\devbrain\Trading_bot"
        if not os.path.exists(trading_bot_path):
            pytest.skip("Trading_bot repository path does not exist")

        analyzer = RepositoryAnalyzer()
        workspace = analyzer.analyze(trading_bot_path)

        assert isinstance(workspace, RepositoryWorkspace)
        assert workspace.repository_name == "Trading_bot"
        assert workspace.statistics.total_files > 0
        assert workspace.statistics.total_loc > 0
        assert len(workspace.analyzable_files) > 0

        # CRITICAL VERIFICATION: Workspace manifest must NOT contain ASTs or Graph nodes
        assert not hasattr(workspace, "ast_root")
        assert not hasattr(workspace, "graph_nodes")
        assert not hasattr(workspace, "edges")
