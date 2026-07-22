import json
import pathlib
import pytest
from typer.testing import CliRunner

from cli.app import app
from core.plugin_manager import PluginManager
from plugins.base import AnalyzerPlugin, PluginMetadata


runner = CliRunner()


def test_cli_version_cmd():
    """Test CLI 'version' command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "DevBrain Repository Analyzer" in result.stdout
    assert "Version & Runtime Info" in result.stdout


def test_cli_config_cmd_table():
    """Test CLI 'config' command with table output."""
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "DevBrain Repository Analyzer Configuration" in result.stdout
    assert "DATABASE_URL" in result.stdout or "database_url" in result.stdout


def test_cli_config_cmd_json():
    """Test CLI 'config --json' command with JSON output."""
    result = runner.invoke(app, ["config", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "environment" in data
    assert "database_url" in data


def test_cli_plugins_cmd(mock_python_plugin):
    """Test CLI 'plugins' command displaying registered plugins."""
    pm = PluginManager.get_instance()
    pm.register(mock_python_plugin)

    result = runner.invoke(app, ["plugins"])
    assert result.exit_code == 0
    assert "Registered Language Analyzer Plugins" in result.stdout
    assert "MockPythonPlugin" in result.stdout
    assert "python" in result.stdout


def test_cli_health_cmd():
    """Test CLI 'health' command."""
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    assert "System Health Report" in result.stdout
    assert "Database" in result.stdout
    assert "Metrics" in result.stdout
    assert "Pipeline" in result.stdout


def test_cli_validate_cmd_success(dummy_repo_dir: pathlib.Path):
    """Test CLI 'validate' command on an existing repository directory."""
    result = runner.invoke(app, ["validate", str(dummy_repo_dir)])
    assert result.exit_code == 0
    assert "Validation Successful!" in result.stdout
    assert "Ready for analysis pipeline" in result.stdout


def test_cli_validate_cmd_nonexistent():
    """Test CLI 'validate' command on a non-existent directory."""
    result = runner.invoke(app, ["validate", "/nonexistent_path_999"])
    assert result.exit_code == 1
    assert "does not exist" in result.stdout


def test_cli_analyze_cmd(dummy_repo_dir: pathlib.Path):
    """Test CLI 'analyze' command displaying summary table."""
    result = runner.invoke(app, ["analyze", str(dummy_repo_dir)])
    assert result.exit_code == 0
    assert "Analysis Summary" in result.stdout
    assert "Pipeline finished successfully!" in result.stdout


def test_cli_analyze_cmd_json(dummy_repo_dir: pathlib.Path):
    """Test CLI 'analyze --json' command returning structured JSON."""
    result = runner.invoke(app, ["analyze", str(dummy_repo_dir), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "run_id" in data
    assert data["status"] == "completed"
    assert "stages_run" in data
    assert len(data["stages_run"]) == 8
