"""
cli/app.py
----------
Typer CLI application for the DevBrain Repository Analyzer V2.
Provides rich commands for analysis, health check, plugin management,
version info, validation, and configuration inspection.
"""

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config.settings import AnalyzerSettings, get_settings
from core.plugin_manager import PluginManager
from models.repository import Repository
from pipeline.context import PipelineContext
from pipeline.pipeline import Pipeline
from storage.postgres import DatabaseManager
from utils.exceptions import AnalyzerBaseError
from utils.logger import get_logger, set_log_context, setup_logging
from utils.metrics import MetricsCollector

app = typer.Typer(
    name="devbrain-analyzer",
    help="DevBrain Repository Analyzer V2 CLI",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()
logger = get_logger("cli")


@app.callback()
def main_callback(
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Set logging level (DEBUG, INFO, WARNING, ERROR)"),
    json_logs: bool = typer.Option(False, "--json-logs", help="Output logs in JSON format"),
) -> None:
    """
    Global CLI setup callback. Configures structured logging.
    """
    setup_logging(log_level=log_level, json_format=json_logs)


@app.command("version")
def version_cmd() -> None:
    """
    Display version, environment, and runtime information.
    """
    settings = get_settings()
    info = (
        f"[bold cyan]DevBrain Repository Analyzer[/bold cyan] v2.0.0\n\n"
        f"[bold]Environment:[/bold] {settings.environment.value}\n"
        f"[bold]Debug Mode:[/bold] {settings.debug_mode}\n"
        f"[bold]Python Version:[/bold] {sys.version.split()[0]}\n"
        f"[bold]Worker Count:[/bold] {settings.worker_count}\n"
        f"[bold]Database URL:[/bold] {settings.database_url.split('@')[-1]}"
    )
    console.print(Panel(info, title="[bold green]Version & Runtime Info[/bold green]", expand=False))


@app.command("config")
def config_cmd(
    as_json: bool = typer.Option(False, "--json", help="Display configuration as JSON"),
) -> None:
    """
    Inspect active configuration settings.
    """
    settings = get_settings()
    if as_json:
        console.print_json(settings.model_dump_json())
    else:
        table = Table(title="DevBrain Repository Analyzer Configuration")
        table.add_column("Setting Key", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        table.add_column("Type", style="green")

        for field_name, field_val in settings.model_dump().items():
            table.add_row(field_name, str(field_val), type(field_val).__name__)

        console.print(table)


@app.command("plugins")
def plugins_cmd() -> None:
    """
    List all discovered and registered analyzer plugins.
    """
    pm = PluginManager.get_instance()
    if not pm.get_all():
        pm.discover_and_load("plugins")

    plugins = pm.get_all()

    if not plugins:
        console.print("[yellow]No plugins registered currently.[/yellow]")
        return

    table = Table(title="Registered Language Analyzer Plugins")
    table.add_column("Plugin Name", style="bold cyan")
    table.add_column("Version", style="green")
    table.add_column("Language", style="magenta")
    table.add_column("Supported Extensions", style="yellow")
    table.add_column("Capabilities", style="white")

    for name, plugin in plugins.items():
        meta = plugin.metadata
        exts = ", ".join(f".{e}" for e in plugin.supported_extensions())
        caps = ", ".join(meta.capabilities)
        table.add_row(meta.name, meta.version, plugin.language(), exts, caps)

    console.print(table)


@app.command("health")
def health_cmd(
    as_json: bool = typer.Option(False, "--json", help="Output health report as JSON"),
    strict_exit: bool = typer.Option(False, "--exit-code", help="Exit with non-zero status code if health status is unhealthy"),
) -> None:
    """
    Run health checks on database, configuration, logging, metrics, pipeline, plugins, and CLI.
    """
    from core.health import HealthChecker
    from models.health import HealthStatus

    checker = HealthChecker()
    report = asyncio.run(checker.run_health_checks())

    if as_json:
        console.print_json(report.model_dump_json())
    else:
        status_color = "green" if report.status == HealthStatus.HEALTHY else ("yellow" if report.status == HealthStatus.DEGRADED else "red")
        table = Table(title=f"System Health Report (Overall Status: [{status_color}]{report.status.value.upper()}[/{status_color}])")
        table.add_column("Subsystem Component", style="bold cyan")
        table.add_column("Status", style="bold")
        table.add_column("Duration (ms)", style="magenta")
        table.add_column("Details / Status Summary", style="white")

        for c in report.components:
            st_color = "green" if c.status == HealthStatus.HEALTHY else ("yellow" if c.status == HealthStatus.DEGRADED else "red")
            st_str = f"[{st_color}]{c.status.value.upper()}[/{st_color}]"

            detail_strs = [f"{k}={v}" for k, v in c.details.items()]
            if c.warnings:
                detail_strs.append(f"warnings: {', '.join(c.warnings)}")
            if c.errors:
                detail_strs.append(f"errors: {', '.join(c.errors)}")

            table.add_row(c.name, st_str, f"{c.duration_ms:.2f}", "; ".join(detail_strs))

        console.print(table)
        console.print(f"[bold]Total Health Check Duration:[/bold] {report.total_duration_ms:.2f} ms")

    if strict_exit and report.status == HealthStatus.UNHEALTHY:
        raise typer.Exit(code=1)


@app.command("validate")
def validate_cmd(
    repo_path: str = typer.Argument(..., help="Path or repository URL to validate"),
) -> None:
    """
    Validate a repository path and structure prior to running analysis.
    """
    path = Path(repo_path)
    if not path.exists():
        console.print(f"[bold red]Error:[/bold red] Repository path '{repo_path}' does not exist.")
        raise typer.Exit(code=1)

    if not path.is_dir():
        console.print(f"[bold red]Error:[/bold red] Path '{repo_path}' is not a directory.")
        raise typer.Exit(code=1)

    files = list(path.glob("**/*"))
    file_count = sum(1 for f in files if f.is_file())

    panel_content = (
        f"[bold green]Validation Successful![/bold green]\n\n"
        f"[bold]Repository Path:[/bold] {path.resolve()}\n"
        f"[bold]Total Files Found:[/bold] {file_count}\n"
        f"[bold]Status:[/bold] Ready for analysis pipeline."
    )
    console.print(Panel(panel_content, title="[bold cyan]Repository Validation[/bold cyan]", expand=False))


@app.command("analyze")
def analyze_cmd(
    repo_path: str = typer.Argument(..., help="Path or URL of repository to analyze"),
    branch: str = typer.Option("main", "--branch", "-b", help="Git branch"),
    output_json: bool = typer.Option(False, "--json", help="Output analysis result summary as JSON"),
) -> None:
    """
    Run repository analysis pipeline (Phase 0 placeholder execution).
    """
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    repo_name = Path(repo_path).name or "sample-repo"

    set_log_context(request_id=f"req-{uuid.uuid4().hex[:6]}", analysis_id=run_id, repository_id=repo_name)

    repo_model = Repository(
        id=f"repo-{uuid.uuid4().hex[:6]}",
        url=repo_path,
        name=repo_name,
        branch=branch,
    )

    ctx = PipelineContext(run_id=run_id, repository=repo_model)
    pipeline = Pipeline()

    try:
        with console.status("[bold green]Executing analysis pipeline...[/bold green]"):
            result_ctx = pipeline.run(ctx)

        metrics = MetricsCollector.get_instance()
        metrics.record_pipeline_duration(run_id, result_ctx.total_duration_ms)

        if output_json:
            out_data = {
                "run_id": result_ctx.run_id,
                "repository_id": result_ctx.repository_id,
                "status": result_ctx.status.value,
                "duration_ms": result_ctx.total_duration_ms,
                "stages_run": [m.stage_name for m in result_ctx.metrics],
                "errors": [e.message for e in result_ctx.errors],
            }
            console.print_json(json.dumps(out_data))
        else:
            table = Table(title=f"Analysis Summary - {repo_name} ({run_id})")
            table.add_column("Stage", style="cyan")
            table.add_column("Duration (ms)", style="magenta")

            for m in result_ctx.metrics:
                table.add_row(m.stage_name, f"{m.duration_ms:.2f}")

            console.print(table)
            console.print(
                f"[bold green]Pipeline finished successfully![/bold green] "
                f"Total Duration: [bold]{result_ctx.total_duration_ms:.2f} ms[/bold]"
            )

    except AnalyzerBaseError as e:
        console.print(f"[bold red]Analyzer Error ({e.code.value}):[/bold red] {e.message}")
        logger.error(f"Analysis failed: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Unexpected Failure:[/bold red] {e}")
        logger.error(f"Unhandled exception during analysis: {e}", exc_info=True)
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
