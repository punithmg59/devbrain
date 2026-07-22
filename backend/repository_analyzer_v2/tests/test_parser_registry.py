"""
tests/test_parser_registry.py
------------------------------
Comprehensive unit and concurrency tests for Phase 3.6 — Parser Registry System.
"""

from __future__ import annotations

import concurrent.futures
import pytest

from core.parser_registry import ParserRegistry, parse_semver_tuple
from models.parser import ParserLanguage
from plugins.parser_plugin import DummyParserPlugin, ParserPlugin
from utils.exceptions import PluginError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_parser_registry():
    """Automatically reset ParserRegistry singleton before every test."""
    ParserRegistry.reset()
    yield
    ParserRegistry.reset()


# ---------------------------------------------------------------------------
# Semver Helper Tests
# ---------------------------------------------------------------------------

def test_parse_semver_tuple():
    assert parse_semver_tuple("1.2.3") == (1, 2, 3)
    assert parse_semver_tuple("v2.10.0-beta") == (2, 10, 0)
    assert parse_semver_tuple("invalid") == (0, 0, 0)


# ---------------------------------------------------------------------------
# Singleton & Reset Tests
# ---------------------------------------------------------------------------

def test_parser_registry_singleton():
    reg1 = ParserRegistry.get_instance()
    reg2 = ParserRegistry.get_instance()
    assert reg1 is reg2

    ParserRegistry.reset()
    reg3 = ParserRegistry.get_instance()
    assert reg3 is not reg1


# ---------------------------------------------------------------------------
# Registration & Indexing Tests
# ---------------------------------------------------------------------------

def test_register_and_lookup_by_language_and_extension():
    reg = ParserRegistry.get_instance()
    py_plugin = DummyParserPlugin(target_language=ParserLanguage.PYTHON)
    ts_plugin = DummyParserPlugin(target_language=ParserLanguage.TYPESCRIPT)

    reg.register(py_plugin)
    reg.register(ts_plugin)

    assert len(reg.list_supported_languages()) == 2
    assert reg.get_by_language(ParserLanguage.PYTHON) is py_plugin
    assert reg.get_by_language("typescript") is ts_plugin

    assert reg.get_by_extension("py") is py_plugin
    assert reg.get_by_extension(".ts") is ts_plugin


def test_register_duplicate_language_raises():
    reg = ParserRegistry.get_instance()
    p1 = DummyParserPlugin(target_language=ParserLanguage.PYTHON)
    p2 = DummyParserPlugin(target_language=ParserLanguage.PYTHON)

    reg.register(p1)
    with pytest.raises(PluginError, match="already registered"):
        reg.register(p2)


def test_lookup_by_capability():
    reg = ParserRegistry.get_instance()
    p1 = DummyParserPlugin(target_language=ParserLanguage.PYTHON)
    reg.register(p1)

    ast_parsers = reg.get_by_capability("supports_ast")
    assert len(ast_parsers) == 1
    assert ast_parsers[0] is p1

    cst_parsers = reg.get_by_capability("supports_cst")
    assert len(cst_parsers) == 0


def test_unregister_plugin():
    reg = ParserRegistry.get_instance()
    p = DummyParserPlugin(target_language=ParserLanguage.JAVA)
    reg.register(p, extensions=["java"])

    assert reg.get_by_language(ParserLanguage.JAVA) is p
    assert reg.get_by_extension("java") is p

    unregistered = reg.unregister(ParserLanguage.JAVA)
    assert unregistered is p
    assert reg.get_by_language(ParserLanguage.JAVA) is None
    assert reg.get_by_extension("java") is None


# ---------------------------------------------------------------------------
# Capabilities & Version Compatibility Tests
# ---------------------------------------------------------------------------

def test_get_capabilities_and_version_compatibility():
    reg = ParserRegistry.get_instance()
    plugin = DummyParserPlugin(target_language=ParserLanguage.GO, semver="1.4.2")
    reg.register(plugin)

    caps = reg.get_capabilities(ParserLanguage.GO)
    assert caps is not None
    assert caps.supports_symbol_extraction is True

    assert reg.check_version_compatibility(ParserLanguage.GO, "1.0.0") is True
    assert reg.check_version_compatibility(ParserLanguage.GO, "1.4.2") is True
    assert reg.check_version_compatibility(ParserLanguage.GO, "2.0.0") is False
    assert reg.check_version_compatibility("unregistered_lang", "1.0.0") is False


# ---------------------------------------------------------------------------
# Plugin Discovery Tests
# ---------------------------------------------------------------------------

def test_discover_and_load_plugins():
    reg = ParserRegistry.get_instance()
    count = reg.discover_and_load("plugins")
    assert isinstance(count, int)


# ---------------------------------------------------------------------------
# Thread Safety Tests
# ---------------------------------------------------------------------------

def test_concurrent_registration_and_lookups():
    reg = ParserRegistry.get_instance()
    languages = [
        ParserLanguage.PYTHON,
        ParserLanguage.TYPESCRIPT,
        ParserLanguage.JAVASCRIPT,
        ParserLanguage.JAVA,
        ParserLanguage.GO,
        ParserLanguage.CSHARP,
    ]

    def register_worker(lang: ParserLanguage):
        plugin = DummyParserPlugin(target_language=lang)
        try:
            reg.register(plugin)
        except PluginError:
            pass

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(register_worker, lang) for lang in languages]
        concurrent.futures.wait(futures)

    assert len(reg.list_supported_languages()) == 6
