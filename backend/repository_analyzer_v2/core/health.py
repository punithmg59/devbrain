import asyncio
import logging
import time
from typing import List, Optional

from config.settings import AnalyzerSettings, get_settings
from core.plugin_manager import PluginManager
from models.health import ComponentHealth, HealthReport, HealthStatus
from storage.postgres import DatabaseManager
from utils.logger import get_logger
from utils.metrics import MetricsCollector

logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Service responsible for conducting comprehensive health checks across all system
    components: Configuration, Plugin Manager, Database, Logging, Metrics, Pipeline, and CLI.
    """

    def __init__(self, settings: Optional[AnalyzerSettings] = None) -> None:
        self._settings = settings

    @property
    def settings(self) -> AnalyzerSettings:
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    async def check_configuration(self) -> ComponentHealth:
        """Check configuration loading and settings bounds."""
        start = time.monotonic()
        warnings: List[str] = []
        errors: List[str] = []
        details = {}

        try:
            s = self.settings
            details["environment"] = s.environment.value
            details["debug_mode"] = s.debug_mode
            details["worker_count"] = s.worker_count

            if s.worker_count > 64:
                warnings.append(f"High worker count ({s.worker_count}) configured.")

        except Exception as e:
            errors.append(f"Configuration check failed: {e}")

        status = HealthStatus.UNHEALTHY if errors else (HealthStatus.DEGRADED if warnings else HealthStatus.HEALTHY)
        duration_ms = (time.monotonic() - start) * 1000

        return ComponentHealth(
            name="Configuration",
            status=status,
            duration_ms=round(duration_ms, 2),
            warnings=warnings,
            errors=errors,
            details=details,
        )

    async def check_plugin_manager(self) -> ComponentHealth:
        """Check PluginManager singleton state and registered plugins."""
        start = time.monotonic()
        warnings: List[str] = []
        errors: List[str] = []
        details = {}

        try:
            pm = PluginManager.get_instance()
            plugins = pm.get_all()
            details["registered_plugins"] = len(plugins)
            details["languages"] = [p.language() for p in plugins.values()]

            if len(plugins) == 0:
                warnings.append("No language plugins currently registered in PluginManager.")

        except Exception as e:
            errors.append(f"PluginManager check failed: {e}")

        status = HealthStatus.UNHEALTHY if errors else (HealthStatus.DEGRADED if warnings else HealthStatus.HEALTHY)
        duration_ms = (time.monotonic() - start) * 1000

        return ComponentHealth(
            name="Plugin Manager",
            status=status,
            duration_ms=round(duration_ms, 2),
            warnings=warnings,
            errors=errors,
            details=details,
        )

    async def check_database(self) -> ComponentHealth:
        """Check database connectivity and responsiveness via SELECT 1."""
        start = time.monotonic()
        warnings: List[str] = []
        errors: List[str] = []
        details = {}

        db = DatabaseManager(self.settings)
        try:
            is_healthy = await db.connect_with_retry(max_retries=1, initial_delay=0.01)
            details["connected"] = is_healthy
            if not is_healthy:
                errors.append("Database health check query returned False.")
        except Exception as e:
            errors.append(f"Database connection check failed: {e}")
            details["connected"] = False
        finally:
            await db.close()

        status = HealthStatus.UNHEALTHY if errors else HealthStatus.HEALTHY
        duration_ms = (time.monotonic() - start) * 1000

        return ComponentHealth(
            name="Database",
            status=status,
            duration_ms=round(duration_ms, 2),
            warnings=warnings,
            errors=errors,
            details=details,
        )

    async def check_logging(self) -> ComponentHealth:
        """Check root logger configuration and structured formatters."""
        start = time.monotonic()
        warnings: List[str] = []
        errors: List[str] = []
        details = {}

        try:
            root = logging.getLogger()
            details["log_level"] = logging.getLevelName(root.level)
            details["handlers_count"] = len(root.handlers)

            if len(root.handlers) == 0:
                warnings.append("No active logging handlers registered on root logger.")

        except Exception as e:
            errors.append(f"Logging check failed: {e}")

        status = HealthStatus.UNHEALTHY if errors else (HealthStatus.DEGRADED if warnings else HealthStatus.HEALTHY)
        duration_ms = (time.monotonic() - start) * 1000

        return ComponentHealth(
            name="Logging",
            status=status,
            duration_ms=round(duration_ms, 2),
            warnings=warnings,
            errors=errors,
            details=details,
        )

    async def check_metrics(self) -> ComponentHealth:
        """Check MetricsCollector singleton and process resource sampling."""
        start = time.monotonic()
        warnings: List[str] = []
        errors: List[str] = []
        details = {}

        try:
            metrics = MetricsCollector.get_instance()
            res = metrics.get_system_resource_usage()
            details["memory_rss_mb"] = res["memory_rss_mb"]
            details["cpu_percent"] = res["cpu_percent"]

            if res["memory_rss_mb"] > 4096.0:
                warnings.append(f"High memory usage detected ({res['memory_rss_mb']} MB).")

        except Exception as e:
            errors.append(f"Metrics check failed: {e}")

        status = HealthStatus.UNHEALTHY if errors else (HealthStatus.DEGRADED if warnings else HealthStatus.HEALTHY)
        duration_ms = (time.monotonic() - start) * 1000

        return ComponentHealth(
            name="Metrics",
            status=status,
            duration_ms=round(duration_ms, 2),
            warnings=warnings,
            errors=errors,
            details=details,
        )

    async def check_pipeline(self) -> ComponentHealth:
        """Check Pipeline instantiation and stage sequence."""
        start = time.monotonic()
        warnings: List[str] = []
        errors: List[str] = []
        details = {}

        try:
            from pipeline.pipeline import DEFAULT_STAGES, Pipeline
            pipeline = Pipeline()
            details["default_stages_count"] = len(pipeline._stages)
            details["stage_names"] = [s.name for s in pipeline._stages]

            if len(pipeline._stages) != 8:
                warnings.append(f"Expected 8 default pipeline stages, found {len(pipeline._stages)}.")

        except Exception as e:
            errors.append(f"Pipeline check failed: {e}")

        status = HealthStatus.UNHEALTHY if errors else (HealthStatus.DEGRADED if warnings else HealthStatus.HEALTHY)
        duration_ms = (time.monotonic() - start) * 1000

        return ComponentHealth(
            name="Pipeline",
            status=status,
            duration_ms=round(duration_ms, 2),
            warnings=warnings,
            errors=errors,
            details=details,
        )

    async def check_cli(self) -> ComponentHealth:
        """Check CLI app importability and command registrations."""
        start = time.monotonic()
        warnings: List[str] = []
        errors: List[str] = []
        details = {}

        try:
            from cli.app import app
            registered_cmds = [cmd.name for cmd in app.registered_commands]
            details["registered_commands"] = registered_cmds

            expected_cmds = {"analyze", "health", "plugins", "version", "validate", "config"}
            missing = expected_cmds - set(registered_cmds)
            if missing:
                warnings.append(f"Missing expected CLI commands: {missing}")

        except Exception as e:
            errors.append(f"CLI check failed: {e}")

        status = HealthStatus.UNHEALTHY if errors else (HealthStatus.DEGRADED if warnings else HealthStatus.HEALTHY)
        duration_ms = (time.monotonic() - start) * 1000

        return ComponentHealth(
            name="CLI",
            status=status,
            duration_ms=round(duration_ms, 2),
            warnings=warnings,
            errors=errors,
            details=details,
        )

    async def run_health_checks(self) -> HealthReport:
        """
        Runs all component health checks concurrently, calculates overall system status,
        and aggregates warnings and errors into a final HealthReport.
        """
        start = time.monotonic()

        components = await asyncio.gather(
            self.check_configuration(),
            self.check_plugin_manager(),
            self.check_database(),
            self.check_logging(),
            self.check_metrics(),
            self.check_pipeline(),
            self.check_cli(),
        )

        all_warnings: List[str] = []
        all_errors: List[str] = []

        overall_status = HealthStatus.HEALTHY

        for c in components:
            all_warnings.extend(c.warnings)
            all_errors.extend(c.errors)
            if c.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif c.status == HealthStatus.DEGRADED and overall_status != HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.DEGRADED

        total_duration_ms = (time.monotonic() - start) * 1000

        return HealthReport(
            status=overall_status,
            total_duration_ms=round(total_duration_ms, 2),
            components=list(components),
            warnings=all_warnings,
            errors=all_errors,
        )
