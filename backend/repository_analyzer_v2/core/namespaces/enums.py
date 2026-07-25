"""
core/namespaces/enums.py
------------------------
Canonical Enums for Namespace Nodes and Trees.
"""

from enum import Enum


class NamespaceKind(str, Enum):
    """Canonical classification of lexical namespace and scope boundaries."""
    REPOSITORY = "repository"
    PACKAGE = "package"
    MODULE = "module"
    NAMESPACE = "namespace"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    LAMBDA = "lambda"
    COMPREHENSION = "comprehension"
    BLOCK = "block"
    ANONYMOUS = "anonymous"
    FUTURE = "future"


class DiagnosticSeverity(str, Enum):
    """Severity levels for namespace construction diagnostics."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
