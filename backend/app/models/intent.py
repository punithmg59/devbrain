from enum import Enum
from typing import Literal


class Intent(str, Enum):
    """Supported intent types for the AI Change Intelligence engine."""
    
    DELETE_CODE = "DELETE_CODE"
    ADD_FEATURE = "ADD_FEATURE"
    MODIFY_CODE = "MODIFY_CODE"
    REFACTOR = "REFACTOR"
    RENAME = "RENAME"
    MOVE = "MOVE"
    DEBUG = "DEBUG"
    ARCHITECTURE = "ARCHITECTURE"
    DEPENDENCY = "DEPENDENCY"
    DATABASE = "DATABASE"
    API = "API"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"
    TESTING = "TESTING"
    SEARCH = "SEARCH"
    GENERAL = "GENERAL"


class TargetType(str, Enum):
    """Target types for code-related intents."""
    
    SERVICE = "service"
    COMPONENT = "component"
    MODULE = "module"
    FUNCTION = "function"
    CLASS = "class"
    FILE = "file"
    VARIABLE = "variable"
    INTERFACE = "interface"
    MODEL = "model"
    ROUTE = "route"
    ENDPOINT = "endpoint"
    REPOSITORY = "repository"
    FOLDER = "folder"
    PACKAGE = "package"
    ENVIRONMENT_VARIABLE = "environment_variable"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"
