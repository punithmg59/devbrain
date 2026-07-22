"""
core/parser_registry.py
------------------------
Phase 3.6 — Parser Registry System.

High-performance, thread-safe registry for registering, looking up, querying capabilities,
verifying version compatibility, and dynamically discovering `ParserPlugin` implementations.

Key Features
------------
- **Thread-Safe Indexing**: Reentrant lock guarding O(1) lookups by language, extension, name,
  and capability flags.
- **Version Compatibility Verification**: Semver comparison routines to verify minimum
  required parser version support.
- **Dynamic Plugin Discovery**: Automatically inspects Python modules to discover and
  instantiate concrete `ParserPlugin` subclasses.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
import re
import threading
from typing import Dict, List, Optional, Set, Type, Union

from models.parser import ParserCapabilities, ParserLanguage, ParserVersion
from plugins.parser_plugin import ParserPlugin
from utils.exceptions import ErrorCode, PluginError

logger = logging.getLogger(__name__)


# Extension mapping for standard languages
_DEFAULT_EXTENSIONS: Dict[ParserLanguage, List[str]] = {
    ParserLanguage.PYTHON: ["py", "pyi"],
    ParserLanguage.TYPESCRIPT: ["ts", "tsx"],
    ParserLanguage.JAVASCRIPT: ["js", "jsx", "mjs", "cjs"],
    ParserLanguage.JAVA: ["java"],
    ParserLanguage.GO: ["go"],
    ParserLanguage.CSHARP: ["cs"],
}


def parse_semver_tuple(ver_str: str) -> tuple[int, int, int]:
    """Parse a semantic version string 'X.Y.Z' into an integer tuple (major, minor, patch)."""
    match = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", ver_str.strip())
    if not match:
        return (0, 0, 0)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


class ParserRegistry:
    """
    Thread-safe registry for DevBrain parser plugins.
    """
    _instance: Optional["ParserRegistry"] = None
    _singleton_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "ParserRegistry":
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(ParserRegistry, cls).__new__(cls)
                cls._instance._init_state()
            return cls._instance

    @classmethod
    def get_instance(cls) -> "ParserRegistry":
        """Singleton accessor for ParserRegistry."""
        return cls()

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton registry instance (useful for test isolation)."""
        with cls._singleton_lock:
            if cls._instance is not None:
                try:
                    cls._instance.clear()
                except Exception as exc:
                    logger.warning(f"[ParserRegistry] Error during reset: {exc}")
                cls._instance = None

    def _init_state(self) -> None:
        """Initialize internal state maps and lock."""
        self._by_language: Dict[ParserLanguage, ParserPlugin] = {}
        self._by_extension: Dict[str, ParserPlugin] = {}
        self._by_name: Dict[str, ParserPlugin] = {}
        self._by_capability: Dict[str, Set[ParserPlugin]] = {}
        self._state_lock: threading.RLock = threading.RLock()

    def clear(self) -> None:
        """Unregister all plugins and clear index maps."""
        with self._state_lock:
            for plugin in list(self._by_language.values()):
                if plugin.is_initialized:
                    try:
                        plugin.shutdown()
                    except Exception as exc:
                        logger.warning(f"[ParserRegistry] Cleanup error: {exc}")
            self._by_language.clear()
            self._by_extension.clear()
            self._by_name.clear()
            self._by_capability.clear()

    # ------------------------------------------------------------------
    # Registration & Unregistration
    # ------------------------------------------------------------------

    def register(self, plugin: ParserPlugin, extensions: Optional[List[str]] = None) -> None:
        """
        Register a `ParserPlugin` instance.

        :param plugin: Concrete `ParserPlugin` instance.
        :param extensions: Optional explicit list of file extensions.
        :raises PluginError: If plugin is invalid or language already registered.
        """
        if not isinstance(plugin, ParserPlugin):
            raise PluginError(
                f"Object '{type(plugin).__name__}' does not inherit from ParserPlugin.",
                code=ErrorCode.PLUGIN_INIT_FAILED,
            )

        lang = plugin.language
        plugin_name = f"ParserPlugin:{lang.value}"

        with self._state_lock:
            if lang in self._by_language:
                raise PluginError(
                    f"Parser plugin for language '{lang.value}' is already registered.",
                    code=ErrorCode.PLUGIN_DUPLICATE,
                )

            # Map language and name
            self._by_language[lang] = plugin
            self._by_name[plugin_name] = plugin

            # Map extensions
            exts = extensions or _DEFAULT_EXTENSIONS.get(lang, [])
            for ext in exts:
                ext_clean = ext.lower().lstrip(".")
                self._by_extension[ext_clean] = plugin

            # Map capabilities
            caps = plugin.capabilities
            if caps.supports_ast:
                self._by_capability.setdefault("supports_ast", set()).add(plugin)
            if caps.supports_cst:
                self._by_capability.setdefault("supports_cst", set()).add(plugin)
            if caps.supports_incremental:
                self._by_capability.setdefault("supports_incremental", set()).add(plugin)
            if caps.supports_symbol_extraction:
                self._by_capability.setdefault("supports_symbol_extraction", set()).add(plugin)
            if caps.supports_import_extraction:
                self._by_capability.setdefault("supports_import_extraction", set()).add(plugin)

        logger.info(f"[ParserRegistry] Registered parser plugin '{plugin_name}' for '{lang.value}'")

    def unregister(self, language: Union[ParserLanguage, str]) -> Optional[ParserPlugin]:
        """
        Unregister a parser plugin for the given language.

        :param language: Target language enum or string.
        :return: Unregistered plugin instance or None.
        """
        target_lang = (
            language if isinstance(language, ParserLanguage)
            else ParserLanguage(language.lower()) if language.lower() in [l.value for l in ParserLanguage]
            else ParserLanguage.UNKNOWN
        )

        with self._state_lock:
            plugin = self._by_language.pop(target_lang, None)
            if not plugin:
                return None

            plugin_name = f"ParserPlugin:{target_lang.value}"
            self._by_name.pop(plugin_name, None)

            # Remove extension references
            for ext, p in list(self._by_extension.items()):
                if p is plugin:
                    del self._by_extension[ext]

            # Remove capability references
            for cap_set in self._by_capability.values():
                cap_set.discard(plugin)

            if plugin.is_initialized:
                try:
                    plugin.shutdown()
                except Exception as exc:
                    logger.warning(f"[ParserRegistry] Shutdown error on unregister: {exc}")

        logger.info(f"[ParserRegistry] Unregistered parser plugin for '{target_lang.value}'")
        return plugin

    # ------------------------------------------------------------------
    # Lookups & Queries
    # ------------------------------------------------------------------

    def get_by_language(self, language: Union[ParserLanguage, str]) -> Optional[ParserPlugin]:
        """Lookup registered parser plugin by language."""
        if isinstance(language, str):
            try:
                target_lang = ParserLanguage(language.lower())
            except ValueError:
                return None
        else:
            target_lang = language

        with self._state_lock:
            return self._by_language.get(target_lang)

    def get_by_extension(self, extension: str) -> Optional[ParserPlugin]:
        """Lookup registered parser plugin by file extension."""
        ext_clean = extension.lower().lstrip(".")
        with self._state_lock:
            return self._by_extension.get(ext_clean)

    def get_by_capability(self, capability: str) -> List[ParserPlugin]:
        """Lookup registered parser plugins matching capability flag name."""
        with self._state_lock:
            return list(self._by_capability.get(capability, set()))

    def list_supported_languages(self) -> List[ParserLanguage]:
        """Return list of supported languages."""
        with self._state_lock:
            return list(self._by_language.keys())

    def get_capabilities(self, language: Union[ParserLanguage, str]) -> Optional[ParserCapabilities]:
        """Get capabilities for a registered language parser."""
        plugin = self.get_by_language(language)
        return plugin.capabilities if plugin else None

    def check_version_compatibility(self, language: Union[ParserLanguage, str], min_version: str) -> bool:
        """
        Check if the registered parser for `language` satisfies `min_version`.

        :param language: Target language.
        :param min_version: Minimum required version string (e.g. '1.0.0').
        :return: True if registered plugin version >= min_version.
        """
        plugin = self.get_by_language(language)
        if not plugin:
            return False

        current_ver = parse_semver_tuple(plugin.version.semver)
        required_ver = parse_semver_tuple(min_version)

        return current_ver >= required_ver

    # ------------------------------------------------------------------
    # Dynamic Plugin Discovery
    # ------------------------------------------------------------------

    def discover_and_load(self, package_name: str = "plugins") -> int:
        """
        Dynamically discover and register concrete `ParserPlugin` subclasses in package.

        :param package_name: Python package name to inspect.
        :return: Number of newly registered plugins.
        """
        logger.info(f"[ParserRegistry] Discovering parser plugins in '{package_name}'...")
        count = 0
        try:
            package = importlib.import_module(package_name)
        except ImportError as exc:
            logger.error(f"[ParserRegistry] Cannot import package '{package_name}': {exc}")
            return 0

        if not hasattr(package, "__path__"):
            return 0

        for _, mod_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            if not is_pkg:
                try:
                    module = importlib.import_module(mod_name)
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(obj, ParserPlugin)
                            and obj is not ParserPlugin
                            and not inspect.isabstract(obj)
                        ):
                            try:
                                plugin_inst = obj()
                                if plugin_inst.language not in self._by_language:
                                    self.register(plugin_inst)
                                    count += 1
                            except Exception as exc:
                                logger.error(f"[ParserRegistry] Failed instantiating '{name}': {exc}")
                except Exception as exc:
                    logger.warning(f"[ParserRegistry] Module import skipped '{mod_name}': {exc}")

        logger.info(f"[ParserRegistry] Discovered and registered {count} parser plugins.")
        return count
