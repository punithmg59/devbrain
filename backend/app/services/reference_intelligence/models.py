"""Reference Intelligence Engine - Data Models."""

from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ReferenceType(str, Enum):
    """Type of reference found."""
    # Source Code
    IMPORT = "import"
    FUNCTION_CALL = "function_call"
    CLASS_INHERITANCE = "class_inheritance"
    INTERFACE_IMPLEMENTATION = "interface_implementation"
    DECORATOR = "decorator"
    ANNOTATION = "annotation"
    
    # Configuration
    ENV_VAR = "env_var"
    YAML_CONFIG = "yaml_config"
    JSON_CONFIG = "json_config"
    TOML_CONFIG = "toml_config"
    INI_CONFIG = "ini_config"
    
    # Infrastructure
    DOCKERFILE = "dockerfile"
    DOCKER_COMPOSE = "docker_compose"
    KUBERNETES = "kubernetes"
    GITHUB_ACTIONS = "github_actions"
    
    # Database
    SQL_MIGRATION = "sql_migration"
    ORM_MODEL = "orm_model"
    FOREIGN_KEY = "foreign_key"
    
    # Runtime
    FASTAPI_ROUTE = "fastapi_route"
    FLASK_ROUTE = "flask_route"
    EXPRESS_ROUTE = "express_route"
    
    # Testing
    PYTEST_TEST = "pytest_test"
    JEST_TEST = "jest_test"
    JUNIT_TEST = "junit_test"


class Criticality(str, Enum):
    """Criticality level of the reference."""
    CRITICAL = "critical"  # Breaking change if modified
    HIGH = "high"  # Significant impact
    MEDIUM = "medium"  # Moderate impact
    LOW = "low"  # Minimal impact
    INFO = "info"  # Informational only


class ReferenceLocation(str, Enum):
    """Location category of the reference."""
    SOURCE_CODE = "source_code"
    CONFIGURATION = "configuration"
    INFRASTRUCTURE = "infrastructure"
    DATABASE = "database"
    RUNTIME = "runtime"
    TEST = "test"


class Reference(BaseModel):
    """A single reference to a repository entity."""
    reference_type: ReferenceType
    reference_location: ReferenceLocation
    file_path: str
    line_number: int
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    criticality: Criticality
    consumer: Optional[str] = Field(None, description="Entity consuming the reference")
    provider: str = Field(..., description="Entity being referenced")
    context: Optional[str] = Field(None, description="Surrounding code context")
    snippet: Optional[str] = Field(None, description="Code snippet containing the reference")


class ReferenceAnalysisResult(BaseModel):
    """Result of reference analysis for a target entity."""
    target_id: UUID
    target_name: str
    target_type: str
    repo_id: UUID
    references: list[Reference] = Field(default_factory=list)
    
    # Summary metrics
    total_references: int = 0
    critical_references: int = 0
    high_references: int = 0
    medium_references: int = 0
    low_references: int = 0
    
    # Breakdown by location
    source_code_references: int = 0
    configuration_references: int = 0
    infrastructure_references: int = 0
    database_references: int = 0
    runtime_references: int = 0
    test_references: int = 0
    
    # Breakdown by type
    import_references: int = 0
    function_call_references: int = 0
    class_inheritance_references: int = 0
    decorator_references: int = 0
    env_var_references: int = 0
    route_references: int = 0
    
    def calculate_metrics(self) -> None:
        """Calculate summary metrics from references."""
        self.total_references = len(self.references)
        
        for ref in self.references:
            # Count by criticality
            if ref.criticality == Criticality.CRITICAL:
                self.critical_references += 1
            elif ref.criticality == Criticality.HIGH:
                self.high_references += 1
            elif ref.criticality == Criticality.MEDIUM:
                self.medium_references += 1
            elif ref.criticality == Criticality.LOW:
                self.low_references += 1
            
            # Count by location
            if ref.reference_location == ReferenceLocation.SOURCE_CODE:
                self.source_code_references += 1
            elif ref.reference_location == ReferenceLocation.CONFIGURATION:
                self.configuration_references += 1
            elif ref.reference_location == ReferenceLocation.INFRASTRUCTURE:
                self.infrastructure_references += 1
            elif ref.reference_location == ReferenceLocation.DATABASE:
                self.database_references += 1
            elif ref.reference_location == ReferenceLocation.RUNTIME:
                self.runtime_references += 1
            elif ref.reference_location == ReferenceLocation.TEST:
                self.test_references += 1
            
            # Count by type
            if ref.reference_type == ReferenceType.IMPORT:
                self.import_references += 1
            elif ref.reference_type == ReferenceType.FUNCTION_CALL:
                self.function_call_references += 1
            elif ref.reference_type == ReferenceType.CLASS_INHERITANCE:
                self.class_inheritance_references += 1
            elif ref.reference_type == ReferenceType.DECORATOR:
                self.decorator_references += 1
            elif ref.reference_type == ReferenceType.ENV_VAR:
                self.env_var_references += 1
            elif ref.reference_type in [ReferenceType.FASTAPI_ROUTE, ReferenceType.FLASK_ROUTE, ReferenceType.EXPRESS_ROUTE]:
                self.route_references += 1


class AnalyzerConfig(BaseModel):
    """Configuration for reference analyzers."""
    repo_id: UUID
    repo_path: str
    target_name: str
    target_id: UUID
    target_type: str
    max_depth: int = 5
    include_tests: bool = True
    include_infrastructure: bool = True
    include_configuration: bool = True
