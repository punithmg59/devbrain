"""
plugins/python/__init__.py
---------------------------
Phase 4.2 — Python Parser Plugin package.
"""

from .python_parser_plugin import PythonParserPlugin
from .semantic_extractor import PythonSemanticExtractor

__all__ = ["PythonParserPlugin", "PythonSemanticExtractor"]
