"""
core/parser_manager.py
----------------------
Phase 3.5 — Parser Manager & Plugin Registry.

Thread-safe, async-capable Singleton manager responsible for loading, registering,
validating, selecting, and executing `ParserPlugin` instances.

Key Features
------------
- **Thread-Safe Singleton**: Implements thread-safe singleton pattern guarded by
  `threading.Lock` with clean `reset()` support for test isolation.
- **Plugin Validation & Registration**: Enforces interface integrity checks before
  registering a `ParserPlugin` for a target `ParserLanguage`.
- **Async Execution Engine**: Asynchronously dispatches `AnalysisJob` processing to the
  selected parser plugin, isolating parser errors and updating `MetricsCollector`.
- **Full Lifecycle Management**: Exposes `initialize_all()`, `shutdown_all()`, and
  `health_check()` across all registered parser plugins.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Union

from core.execution_context import ExecutionContext
from core.tree_sitter_engine import TreeSitterEngine
from models.health import ComponentHealth, HealthStatus
from models.job import AnalysisJob
from models.parser import (
    ParserLanguage,
    ParserMetadata,
    ParserOptions,
    ParserResult,
    ParserStatistics,
    ParserStatus,
    ParserVersion,
)
from plugins.parser_plugin import ParserPlugin
from utils.exceptions import ErrorCode, ParserError, PluginError
from utils.metrics import MetricsCollector

logger = logging.getLogger(__name__)


# Standard extension-to-language mappings
_EXTENSION_TO_LANGUAGE: Dict[str, ParserLanguage] = {
    "py": ParserLanguage.PYTHON,
    "pyi": ParserLanguage.PYTHON,
    "ts": ParserLanguage.TYPESCRIPT,
    "tsx": ParserLanguage.TYPESCRIPT,
    "js": ParserLanguage.JAVASCRIPT,
    "jsx": ParserLanguage.JAVASCRIPT,
    "java": ParserLanguage.JAVA,
    "go": ParserLanguage.GO,
    "cs": ParserLanguage.CSHARP,
}


class ParserManager:
    """
    Thread-safe Singleton manager for parser plugins in DevBrain.
    """
    _instance: Optional["ParserManager"] = None
    _singleton_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "ParserManager":
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(ParserManager, cls).__new__(cls)
                cls._instance._init_state()
            return cls._instance

    @classmethod
    def get_instance(cls) -> "ParserManager":
        """Singleton accessor for ParserManager."""
        return cls()

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (useful for test suite isolation)."""
        with cls._singleton_lock:
            if cls._instance is not None:
                try:
                    cls._instance.shutdown_all()
                except Exception as exc:
                    logger.warning(f"[ParserManager] Error during reset shutdown: {exc}")
                cls._instance = None

    def _init_state(self) -> None:
        """Initialize internal registries, engine, and state lock."""
        self._parsers: Dict[ParserLanguage, ParserPlugin] = {}
        self._state_lock: threading.Lock = threading.Lock()
        self._metrics: MetricsCollector = MetricsCollector.get_instance()
        # Phase 4.1: Tree-sitter engine (lazily or explicitly initialized)
        self._engine: Optional[TreeSitterEngine] = None

    # ------------------------------------------------------------------
    # Validation & Registration
    # ------------------------------------------------------------------

    def validate_parser(self, plugin: ParserPlugin) -> bool:
        """
        Validate whether a plugin instance correctly implements the `ParserPlugin` contract.

        :param plugin: Object to validate.
        :return: True if valid.
        :raises PluginError: If validation fails.
        """
        if not isinstance(plugin, ParserPlugin):
            raise PluginError(
                f"Object '{type(plugin).__name__}' does not inherit from ParserPlugin.",
                code=ErrorCode.PLUGIN_INIT_FAILED,
            )

        try:
            lang = plugin.language
            if not isinstance(lang, ParserLanguage):
                raise PluginError(
                    f"Plugin '{type(plugin).__name__}' language property must return ParserLanguage enum.",
                    code=ErrorCode.PLUGIN_INIT_FAILED,
                )
            _ = plugin.version
            _ = plugin.capabilities
        except Exception as exc:
            raise PluginError(
                f"Plugin '{type(plugin).__name__}' failed contract validation: {exc}",
                code=ErrorCode.PLUGIN_INIT_FAILED,
            ) from exc

        return True

    def register_parser(self, plugin: ParserPlugin) -> None:
        """
        Register a validated `ParserPlugin` instance.

        :param plugin: Instantiated `ParserPlugin`.
        :raises PluginError: If plugin validation fails or language already registered.
        """
        self.validate_parser(plugin)
        lang = plugin.language

        with self._state_lock:
            if lang in self._parsers:
                raise PluginError(
                    f"Parser plugin for language '{lang.value}' is already registered.",
                    code=ErrorCode.PLUGIN_DUPLICATE,
                )
            self._parsers[lang] = plugin

        logger.info(f"[ParserManager] Registered parser plugin for language '{lang.value}'")

    def unregister_parser(self, language: Union[ParserLanguage, str]) -> Optional[ParserPlugin]:
        """
        Unregister a parser plugin for the given language.

        :param language: Target language enum or string.
        :return: The unregistered plugin or None.
        """
        target_lang = (
            language if isinstance(language, ParserLanguage)
            else ParserLanguage(language.lower()) if language.lower() in [l.value for l in ParserLanguage]
            else ParserLanguage.UNKNOWN
        )

        with self._state_lock:
            plugin = self._parsers.pop(target_lang, None)

        if plugin and plugin.is_initialized:
            try:
                plugin.shutdown()
            except Exception as exc:
                logger.warning(f"[ParserManager] Error shutting down plugin '{target_lang.value}': {exc}")

        if plugin:
            logger.info(f"[ParserManager] Unregistered parser plugin for '{target_lang.value}'")
        return plugin

    # ------------------------------------------------------------------
    # Selection & Lookup
    # ------------------------------------------------------------------

    def select_parser(self, language: Union[ParserLanguage, str]) -> Optional[ParserPlugin]:
        """
        Select a registered `ParserPlugin` by language.

        :param language: Target `ParserLanguage` enum or string name.
        :return: Matching `ParserPlugin` instance, or None if unsupported.
        """
        if isinstance(language, str):
            lang_str = language.lower()
            try:
                target_lang = ParserLanguage(lang_str)
            except ValueError:
                return None
        else:
            target_lang = language

        with self._state_lock:
            return self._parsers.get(target_lang)

    def select_parser_by_file(self, file_path_or_ext: str) -> Optional[ParserPlugin]:
        """
        Select a registered `ParserPlugin` by file extension or path.

        :param file_path_or_ext: File path or extension string.
        :return: Matching `ParserPlugin` instance or None.
        """
        ext = file_path_or_ext.rsplit(".", 1)[-1].lower() if "." in file_path_or_ext else file_path_or_ext.lower()
        target_lang = _EXTENSION_TO_LANGUAGE.get(ext)
        if not target_lang:
            return None
        return self.select_parser(target_lang)

    def get_registered_languages(self) -> List[ParserLanguage]:
        """Return a list of all currently registered languages."""
        with self._state_lock:
            return list(self._parsers.keys())

    # ------------------------------------------------------------------
    # Async Parser Execution
    # ------------------------------------------------------------------

    async def execute_parser(
        self,
        job: AnalysisJob,
        context: ExecutionContext,
        options: Optional[ParserOptions] = None,
    ) -> ParserResult:
        """
        Asynchronously execute parsing for an `AnalysisJob` using the appropriate `ParserPlugin`.

        :param job: AnalysisJob carrying file payload.
        :param context: Worker ExecutionContext.
        :param options: Optional ParserOptions.
        :return: ParserResult object.
        """
        start_time = time.monotonic()
        lang_str = job.language or job.file.language

        # Select parser plugin
        plugin = self.select_parser(lang_str) or self.select_parser_by_file(job.file.extension)

        if not plugin:
            err_msg = f"No parser plugin registered for language '{lang_str}' ({job.file.path})."
            logger.warning(f"[ParserManager] {err_msg}")
            return ParserResult(
                job_id=job.job_id,
                file_path=job.file.path,
                language=ParserLanguage.UNKNOWN,
                status=ParserStatus.UNSUPPORTED_LANGUAGE,
                metadata=ParserMetadata(
                    parser_name="unsupported",
                    language=ParserLanguage.UNKNOWN,
                    version=ParserVersion(semver="0.0.0"),
                ),
            )

        # Initialize plugin if needed
        if not plugin.is_initialized:
            try:
                plugin.initialize()
            except Exception as exc:
                err_msg = f"Failed to initialize parser plugin for '{plugin.language.value}': {exc}"
                logger.error(f"[ParserManager] {err_msg}")
                return ParserResult(
                    job_id=job.job_id,
                    file_path=job.file.path,
                    language=plugin.language,
                    status=ParserStatus.INTERNAL_ERROR,
                    metadata=ParserMetadata(
                        parser_name=f"parser-{plugin.language.value}",
                        language=plugin.language,
                        version=plugin.version,
                    ),
                )

        # Execute parse with error isolation
        try:
            # Yield to event loop before sync parse call
            await asyncio.sleep(0.001)

            result = plugin.parse(job, context, options)
            duration_ms = (time.monotonic() - start_time) * 1000.0
            # Record metrics & telemetry (Phase 3.8)
            resource_usage = self._metrics.get_system_resource_usage()
            ast_nodes = result.statistics.node_count if result.statistics else 0
            warn_count = len(result.warnings)
            err_count = len(result.errors)

            from models.parser import ParserFileMetrics
            file_metric = ParserFileMetrics(
                file_path=job.file.path,
                language=plugin.language,
                plugin_name=result.metadata.parser_name if result.metadata else f"parser-{plugin.language.value}",
                parser_version=result.metadata.version.semver if (result.metadata and result.metadata.version) else plugin.version.semver,
                duration_ms=round(duration_ms, 2),
                ast_node_count=ast_nodes,
                memory_rss_mb=resource_usage["memory_rss_mb"],
                warning_count=warn_count,
                error_count=err_count,
            )
            self._metrics.record_parser_file_metrics(context.pipeline_context.run_id, file_metric)
            self._metrics.record_stage_duration(context.pipeline_context.run_id, "Parser", duration_ms)
            logger.debug(f"[ParserManager] Executed parser '{plugin.language.value}' for '{job.file.path}' in {duration_ms:.2f}ms")
            return result

        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000.0
            logger.error(f"[ParserManager] Unhandled parse exception on '{job.file.path}': {exc}", exc_info=True)
            self._metrics.increment_error_count(context.pipeline_context.run_id, 1)

            resource_usage = self._metrics.get_system_resource_usage()
            from models.parser import ParserFileMetrics
            file_metric = ParserFileMetrics(
                file_path=job.file.path,
                language=plugin.language,
                plugin_name=f"parser-{plugin.language.value}",
                parser_version=plugin.version.semver,
                duration_ms=round(duration_ms, 2),
                ast_node_count=0,
                memory_rss_mb=resource_usage["memory_rss_mb"],
                warning_count=0,
                error_count=1,
            )
            self._metrics.record_parser_file_metrics(context.pipeline_context.run_id, file_metric)

            from models.parser import ParserError as ModelParserError
            return ParserResult(
                job_id=job.job_id,
                file_path=job.file.path,
                language=plugin.language,
                status=ParserStatus.INTERNAL_ERROR,
                errors=[ModelParserError(message=f"Parser execution crash: {exc}")],
                metadata=ParserMetadata(
                    parser_name=f"parser-{plugin.language.value}",
                    language=plugin.language,
                    version=plugin.version,
                ),
            )

    # ------------------------------------------------------------------
    # Lifecycle Operations
    # ------------------------------------------------------------------

    def initialize_all(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize all registered parser plugins and the Tree-sitter engine."""
        with self._state_lock:
            for lang, plugin in self._parsers.items():
                if not plugin.is_initialized:
                    try:
                        plugin.initialize(config)
                        logger.info(f"[ParserManager] Initialized parser plugin '{lang.value}'")
                    except Exception as exc:
                        logger.error(f"[ParserManager] Failed initializing plugin '{lang.value}': {exc}")

        # Initialize Tree-sitter engine for all supported languages
        if self._engine is None:
            self._engine = TreeSitterEngine()
        if not self._engine._is_initialized:
            try:
                self._engine.initialize()
                logger.info("[ParserManager] TreeSitterEngine initialized.")
            except Exception as exc:
                logger.error(f"[ParserManager] TreeSitterEngine initialization failed: {exc}")

    def shutdown_all(self) -> None:
        """Shutdown all registered parser plugins and release Tree-sitter engine resources."""
        with self._state_lock:
            for lang, plugin in self._parsers.items():
                if plugin.is_initialized:
                    try:
                        plugin.shutdown()
                        logger.info(f"[ParserManager] Shut down parser plugin '{lang.value}'")
                    except Exception as exc:
                        logger.warning(f"[ParserManager] Error shutting down plugin '{lang.value}': {exc}")

        if self._engine is not None:
            try:
                self._engine.shutdown()
                logger.info("[ParserManager] TreeSitterEngine shut down.")
            except Exception as exc:
                logger.warning(f"[ParserManager] Error shutting down TreeSitterEngine: {exc}")
            self._engine = None

    def health_check(self) -> Dict[str, ComponentHealth]:
        """Collect health check status across all registered parser plugins and engine."""
        health_map: Dict[str, ComponentHealth] = {}
        with self._state_lock:
            for lang, plugin in self._parsers.items():
                try:
                    health_map[lang.value] = plugin.health()
                except Exception as exc:
                    health_map[lang.value] = ComponentHealth(
                        name=f"ParserPlugin:{lang.value}",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Health check exception: {exc}",
                    )

        # Include Tree-sitter engine health
        if self._engine is not None:
            try:
                health_map["tree_sitter_engine"] = self._engine.component_health()
            except Exception as exc:
                health_map["tree_sitter_engine"] = ComponentHealth(
                    name="TreeSitterEngine",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check exception: {exc}",
                )
        return health_map

    def get_engine(self) -> Optional[TreeSitterEngine]:
        """Return the ``TreeSitterEngine`` instance (internal use only — do not expose native tree-sitter objects)."""
        return self._engine

    def initialize_engine(self, languages: Optional[List[ParserLanguage]] = None) -> None:
        """
        Explicitly initialize the ``TreeSitterEngine`` for specific languages.

        This is the preferred entry point when a caller wants tree-sitter backend
        parsing without triggering full ``initialize_all()``.
        """
        if self._engine is None:
            self._engine = TreeSitterEngine()
        if not self._engine._is_initialized:
            self._engine.initialize(languages)
            logger.info("[ParserManager] TreeSitterEngine initialized via initialize_engine().")
