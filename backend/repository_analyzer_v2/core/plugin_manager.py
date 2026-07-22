import importlib
import logging
import pkgutil
import threading
from typing import Dict, Optional, Type

from plugins.base import AnalyzerPlugin
from utils.exceptions import PluginError  # canonical exception

logger = logging.getLogger(__name__)




class PluginManager:
    """
    A thread-safe Singleton manager for discovering, registering, and retrieving 
    Repository Analyzer plugins.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PluginManager, cls).__new__(cls)
                cls._instance._init_state()
            return cls._instance

    @classmethod
    def get_instance(cls) -> "PluginManager":
        """Singleton accessor for PluginManager."""
        return cls()

    def _init_state(self):
        """Initialize the internal state for the singleton."""
        self._plugins: Dict[str, AnalyzerPlugin] = {}
        self._plugins_by_language: Dict[str, AnalyzerPlugin] = {}
        self._plugins_by_extension: Dict[str, AnalyzerPlugin] = {}
        self._state_lock = threading.Lock()

    def register(self, plugin: AnalyzerPlugin) -> None:
        """
        Register an instantiated plugin.
        Validates for duplicates, valid versions, and proper extensions.
        """
        with self._state_lock:
            name = plugin.metadata.name
            
            # Basic validation
            if name in self._plugins:
                raise PluginError(f"Plugin '{name}' is already registered.")
            
            lang = plugin.language().lower()
            if lang in self._plugins_by_language:
                raise PluginError(f"Language '{lang}' is already supported by another plugin.")

            extensions = plugin.supported_extensions()
            if not extensions:
                raise PluginError(f"Plugin '{name}' must support at least one extension.")
                
            for ext in extensions:
                ext_clean = ext.lower().lstrip(".")
                if ext_clean in self._plugins_by_extension:
                    raise PluginError(
                        f"Extension '{ext_clean}' is already registered by "
                        f"'{self._plugins_by_extension[ext_clean].metadata.name}'."
                    )
            
            # Registration
            self._plugins[name] = plugin
            self._plugins_by_language[lang] = plugin
            for ext in extensions:
                ext_clean = ext.lower().lstrip(".")
                self._plugins_by_extension[ext_clean] = plugin
                
            logger.info(f"Registered plugin '{name}' v{plugin.metadata.version} for language '{lang}'.")

    def unregister(self, plugin_name: str) -> None:
        """
        Unload and unregister a plugin by its name.
        Calls the plugin's cleanup method.
        """
        with self._state_lock:
            if plugin_name not in self._plugins:
                logger.warning(f"Attempted to unregister unknown plugin '{plugin_name}'.")
                return
                
            plugin = self._plugins[plugin_name]
            lang = plugin.language().lower()
            extensions = [ext.lower().lstrip(".") for ext in plugin.supported_extensions()]
            
            # Clean up resources
            try:
                plugin.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup of plugin '{plugin_name}': {e}")
            
            # Remove from registries
            del self._plugins[plugin_name]
            
            if lang in self._plugins_by_language:
                del self._plugins_by_language[lang]
                
            for ext in extensions:
                if ext in self._plugins_by_extension:
                    del self._plugins_by_extension[ext]
                    
            logger.info(f"Unregistered plugin '{plugin_name}'.")

    def get_by_language(self, language: str) -> Optional[AnalyzerPlugin]:
        """Return a registered plugin for a specific language."""
        with self._state_lock:
            return self._plugins_by_language.get(language.lower())

    def get_by_extension(self, extension: str) -> Optional[AnalyzerPlugin]:
        """Return a registered plugin for a specific file extension."""
        with self._state_lock:
            ext_clean = extension.lower().lstrip(".")
            return self._plugins_by_extension.get(ext_clean)

    def get_all(self) -> Dict[str, AnalyzerPlugin]:
        """Return all registered plugins."""
        with self._state_lock:
            return self._plugins.copy()

    def discover_and_load(self, package_name: str = "plugins") -> None:
        """
        Dynamically discover and instantiate AnalyzerPlugins from a given package.
        Looks for all subclasses of AnalyzerPlugin in the modules of the package.
        """
        logger.info(f"Discovering plugins in package '{package_name}'...")
        try:
            package = importlib.import_module(package_name)
        except ImportError as e:
            logger.error(f"Could not import package '{package_name}' for discovery: {e}")
            return

        if not hasattr(package, "__path__"):
            logger.error(f"'{package_name}' is not a package.")
            return

        for _, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            if not is_pkg:
                try:
                    module = importlib.import_module(module_name)
                    self._load_plugins_from_module(module)
                except Exception as e:
                    logger.error(f"Failed to load module '{module_name}': {e}")

    def _load_plugins_from_module(self, module) -> None:
        """Helper to find and register AnalyzerPlugin subclasses in a module."""
        import inspect
        
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, AnalyzerPlugin) and obj is not AnalyzerPlugin:
                # Do not instantiate if it's still abstract
                if not inspect.isabstract(obj):
                    try:
                        plugin_instance = obj()
                        # Only register if not already registered (avoid conflicts if same module loaded twice)
                        if plugin_instance.metadata.name not in self._plugins:
                            self.register(plugin_instance)
                    except Exception as e:
                        logger.error(f"Failed to instantiate or register plugin '{name}': {e}")
