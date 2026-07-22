import json
import pytest
from typer.testing import CliRunner

from cli.app import app
from core.health import HealthChecker
from models.health import ComponentHealth, HealthReport, HealthStatus


runner = CliRunner()


def test_health_models():
    """Test ComponentHealth and HealthReport model instantiation and JSON serialization."""
    comp = ComponentHealth(
        name="TestComp",
        status=HealthStatus.HEALTHY,
        duration_ms=12.34,
        details={"key": "val"},
    )
    assert comp.name == "TestComp"
    assert comp.status == HealthStatus.HEALTHY

    report = HealthReport(
        status=HealthStatus.HEALTHY,
        total_duration_ms=50.0,
        components=[comp],
    )
    assert report.status == HealthStatus.HEALTHY
    assert len(report.components) == 1

    json_data = json.loads(report.model_dump_json())
    assert json_data["status"] == "healthy"
    assert json_data["components"][0]["name"] == "TestComp"


@pytest.mark.asyncio
async def test_health_checker_individual_checks():
    """Test running individual health check methods in HealthChecker."""
    checker = HealthChecker()

    config_c = await checker.check_configuration()
    assert config_c.name == "Configuration"
    assert config_c.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)

    plugin_c = await checker.check_plugin_manager()
    assert plugin_c.name == "Plugin Manager"

    logging_c = await checker.check_logging()
    assert logging_c.name == "Logging"

    metrics_c = await checker.check_metrics()
    assert metrics_c.name == "Metrics"

    pipeline_c = await checker.check_pipeline()
    assert pipeline_c.name == "Pipeline"
    assert pipeline_c.details["default_stages_count"] == 8

    cli_c = await checker.check_cli()
    assert cli_c.name == "CLI"
    assert "analyze" in cli_c.details["registered_commands"]


@pytest.mark.asyncio
async def test_health_checker_full_run():
    """Test run_health_checks aggregates all 7 component checks."""
    checker = HealthChecker()
    report = await checker.run_health_checks()

    assert isinstance(report, HealthReport)
    assert len(report.components) == 7
    component_names = {c.name for c in report.components}
    expected_names = {"Configuration", "Plugin Manager", "Database", "Logging", "Metrics", "Pipeline", "CLI"}
    assert component_names == expected_names
    assert report.total_duration_ms > 0.0


def test_cli_health_cmd_text():
    """Test CLI 'health' command with formatted table output."""
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    assert "System Health Report" in result.stdout
    assert "Configuration" in result.stdout
    assert "Plugin Manager" in result.stdout
    assert "Database" in result.stdout
    assert "Pipeline" in result.stdout


def test_cli_health_cmd_json():
    """Test CLI 'health --json' command returning structured JSON."""
    result = runner.invoke(app, ["health", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "status" in data
    assert "components" in data
    assert len(data["components"]) == 7
