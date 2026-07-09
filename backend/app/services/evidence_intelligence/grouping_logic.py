"""Evidence Intelligence Engine - Grouping Logic."""

import logging
from typing import List

from app.services.reference_intelligence.models import Reference, ReferenceType, ReferenceLocation
from .models import EvidenceCategory, EvidenceGroup, FailureMode, Criticality

logger = logging.getLogger(__name__)


class GroupingLogic:
    """Groups references into evidence categories."""
    
    @staticmethod
    def group_references(references: List[Reference]) -> dict[EvidenceCategory, List[Reference]]:
        """
        Group references into evidence categories.
        
        Args:
            references: List of references to group
            
        Returns:
            Dictionary mapping categories to reference lists
        """
        groups = {
            EvidenceCategory.RUNTIME_DEPENDENCIES: [],
            EvidenceCategory.CONFIGURATION_DEPENDENCIES: [],
            EvidenceCategory.INFRASTRUCTURE_DEPENDENCIES: [],
            EvidenceCategory.DATABASE_DEPENDENCIES: [],
            EvidenceCategory.TESTING_DEPENDENCIES: [],
            EvidenceCategory.PUBLIC_API_DEPENDENCIES: [],
            EvidenceCategory.INTERNAL_DEPENDENCIES: [],
        }
        
        for ref in references:
            category = GroupingLogic._determine_category(ref)
            groups[category].append(ref)
        
        return groups
    
    @staticmethod
    def _determine_category(ref: Reference) -> EvidenceCategory:
        """
        Determine the evidence category for a reference.
        
        Args:
            ref: Reference to categorize
            
        Returns:
            EvidenceCategory for the reference
        """
        # Runtime dependencies: function calls, routes, runtime references
        if ref.reference_type in {
            ReferenceType.FUNCTION_CALL,
            ReferenceType.FASTAPI_ROUTE,
            ReferenceType.FLASK_ROUTE,
            ReferenceType.EXPRESS_ROUTE
        }:
            return EvidenceCategory.RUNTIME_DEPENDENCIES
        
        # Configuration dependencies: env vars, config files
        if ref.reference_type in {
            ReferenceType.ENV_VAR,
            ReferenceType.YAML_CONFIG,
            ReferenceType.JSON_CONFIG,
            ReferenceType.TOML_CONFIG,
            ReferenceType.INI_CONFIG
        }:
            return EvidenceCategory.CONFIGURATION_DEPENDENCIES
        
        # Infrastructure dependencies: Docker, K8s, GitHub Actions
        if ref.reference_type in {
            ReferenceType.DOCKERFILE,
            ReferenceType.DOCKER_COMPOSE,
            ReferenceType.KUBERNETES,
            ReferenceType.GITHUB_ACTIONS
        }:
            return EvidenceCategory.INFRASTRUCTURE_DEPENDENCIES
        
        # Database dependencies: SQL migrations, ORM, foreign keys
        if ref.reference_type in {
            ReferenceType.SQL_MIGRATION,
            ReferenceType.ORM_MODEL,
            ReferenceType.FOREIGN_KEY
        }:
            return EvidenceCategory.DATABASE_DEPENDENCIES
        
        # Testing dependencies: pytest, jest, junit
        if ref.reference_type in {
            ReferenceType.PYTEST_TEST,
            ReferenceType.JEST_TEST,
            ReferenceType.JUNIT_TEST
        }:
            return EvidenceCategory.TESTING_DEPENDENCIES
        
        # Public API dependencies: API routes, public interfaces
        if ref.reference_type == ReferenceType.API_ROUTE or ref.reference_location == ReferenceLocation.RUNTIME:
            return EvidenceCategory.PUBLIC_API_DEPENDENCIES
        
        # Internal dependencies: imports, inheritance, decorators, annotations
        if ref.reference_type in {
            ReferenceType.IMPORT,
            ReferenceType.CLASS_INHERITANCE,
            ReferenceType.INTERFACE_IMPLEMENTATION,
            ReferenceType.DECORATOR,
            ReferenceType.ANNOTATION
        }:
            return EvidenceCategory.INTERNAL_DEPENDENCIES
        
        # Default to internal dependencies
        return EvidenceCategory.INTERNAL_DEPENDENCIES
    
    @staticmethod
    def determine_failure_mode(category: EvidenceCategory, references: List[Reference]) -> FailureMode:
        """
        Determine the estimated failure mode for a category.
        
        Args:
            category: Evidence category
            references: References in the category
            
        Returns:
            Estimated failure mode
        """
        if not references:
            return FailureMode.UNKNOWN
        
        # Check for critical references
        has_critical = any(ref.criticality == Criticality.CRITICAL for ref in references)
        
        if category == EvidenceCategory.RUNTIME_DEPENDENCIES:
            if has_critical:
                return FailureMode.RUNTIME_ERROR
            return FailureMode.SERVICE_UNAVAILABLE
        
        elif category == EvidenceCategory.CONFIGURATION_DEPENDENCIES:
            return FailureMode.CONFIGURATION_ERROR
        
        elif category == EvidenceCategory.INFRASTRUCTURE_DEPENDENCIES:
            return FailureMode.DEPLOYMENT_ERROR
        
        elif category == EvidenceCategory.DATABASE_DEPENDENCIES:
            if has_critical:
                return FailureMode.DATA_CORRUPTION
            return FailureMode.RUNTIME_ERROR
        
        elif category == EvidenceCategory.TESTING_DEPENDENCIES:
            return FailureMode.TEST_FAILURE
        
        elif category == EvidenceCategory.PUBLIC_API_DEPENDENCIES:
            if has_critical:
                return FailureMode.API_FAILURE
            return FailureMode.SERVICE_UNAVAILABLE
        
        elif category == EvidenceCategory.INTERNAL_DEPENDENCIES:
            # Check if imports are critical
            import_refs = [r for r in references if r.reference_type == ReferenceType.IMPORT]
            if any(r.criticality == Criticality.CRITICAL for r in import_refs):
                return FailureMode.BUILD_ERROR
            return FailureMode.RUNTIME_ERROR
        
        return FailureMode.UNKNOWN
