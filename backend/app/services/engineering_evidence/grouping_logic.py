"""Engineering Evidence Engine - Grouping Logic."""

import logging
from typing import List, Set

from app.services.reference_intelligence.models import Reference, ReferenceType, ReferenceLocation
from .models import EvidenceCategory, FailureMode, Criticality

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
            EvidenceCategory.RUNTIME: [],
            EvidenceCategory.CONFIGURATION: [],
            EvidenceCategory.INFRASTRUCTURE: [],
            EvidenceCategory.DATABASE: [],
            EvidenceCategory.TESTING: [],
            EvidenceCategory.PUBLIC_API: [],
            EvidenceCategory.INTERNAL_SERVICE: [],
            EvidenceCategory.EXTERNAL_DEPENDENCY: [],
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
        # Public API dependencies: API routes, public interfaces (check first)
        if ref.reference_location == ReferenceLocation.RUNTIME and ref.reference_type in {
            ReferenceType.FASTAPI_ROUTE,
            ReferenceType.FLASK_ROUTE,
            ReferenceType.EXPRESS_ROUTE
        }:
            return EvidenceCategory.PUBLIC_API
        
        # Runtime dependencies: function calls, runtime references
        if ref.reference_type in {
            ReferenceType.FUNCTION_CALL,
        }:
            return EvidenceCategory.RUNTIME
        
        # Configuration dependencies: env vars, config files
        if ref.reference_type in {
            ReferenceType.ENV_VAR,
            ReferenceType.YAML_CONFIG,
            ReferenceType.JSON_CONFIG,
            ReferenceType.TOML_CONFIG,
            ReferenceType.INI_CONFIG
        }:
            return EvidenceCategory.CONFIGURATION
        
        # Infrastructure dependencies: Docker, K8s, GitHub Actions
        if ref.reference_type in {
            ReferenceType.DOCKERFILE,
            ReferenceType.DOCKER_COMPOSE,
            ReferenceType.KUBERNETES,
            ReferenceType.GITHUB_ACTIONS
        }:
            return EvidenceCategory.INFRASTRUCTURE
        
        # Database dependencies: SQL migrations, ORM, foreign keys
        if ref.reference_type in {
            ReferenceType.SQL_MIGRATION,
            ReferenceType.ORM_MODEL,
            ReferenceType.FOREIGN_KEY
        }:
            return EvidenceCategory.DATABASE
        
        # Testing dependencies: pytest, jest, junit
        if ref.reference_type in {
            ReferenceType.PYTEST_TEST,
            ReferenceType.JEST_TEST,
            ReferenceType.JUNIT_TEST
        }:
            return EvidenceCategory.TESTING
        
        # Public API dependencies: API routes, public interfaces
        if ref.reference_location == ReferenceLocation.RUNTIME:
            return EvidenceCategory.PUBLIC_API
        
        # Internal services: internal service references
        if ref.consumer and ref.consumer != ref.provider:
            # This is a service-to-service reference
            return EvidenceCategory.INTERNAL_SERVICE
        
        # External dependencies: imports from external packages
        if ref.reference_type == ReferenceType.IMPORT:
            # Check if this is an external package (not internal)
            # External packages typically are all lowercase (e.g., numpy, pandas, requests)
            # Internal imports have PascalCase in the path (e.g., auth.utils.AuthHelper)
            if ref.provider and not ref.provider.startswith('.'):
                # Check if any part of the path is PascalCase (indicates internal)
                parts = ref.provider.split('.')
                has_pascal_case = any(part[0].isupper() if part else False for part in parts)
                if not has_pascal_case and ref.provider.islower():
                    return EvidenceCategory.EXTERNAL_DEPENDENCY
        
        # Default to runtime for function calls and internal for others
        if ref.reference_type == ReferenceType.FUNCTION_CALL:
            return EvidenceCategory.RUNTIME
        
        # Internal dependencies: imports, inheritance, decorators, annotations
        if ref.reference_type in {
            ReferenceType.IMPORT,
            ReferenceType.CLASS_INHERITANCE,
            ReferenceType.INTERFACE_IMPLEMENTATION,
            ReferenceType.DECORATOR,
            ReferenceType.ANNOTATION
        }:
            return EvidenceCategory.INTERNAL_SERVICE
        
        # Default to internal service
        return EvidenceCategory.INTERNAL_SERVICE
    
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
        
        if category == EvidenceCategory.RUNTIME:
            if has_critical:
                return FailureMode.RUNTIME_ERROR
            return FailureMode.SERVICE_UNAVAILABLE
        
        elif category == EvidenceCategory.CONFIGURATION:
            return FailureMode.CONFIGURATION_ERROR
        
        elif category == EvidenceCategory.INFRASTRUCTURE:
            return FailureMode.DEPLOYMENT_ERROR
        
        elif category == EvidenceCategory.DATABASE:
            if has_critical:
                return FailureMode.DATA_CORRUPTION
            return FailureMode.RUNTIME_ERROR
        
        elif category == EvidenceCategory.TESTING:
            return FailureMode.TEST_FAILURE
        
        elif category == EvidenceCategory.PUBLIC_API:
            if has_critical:
                return FailureMode.API_FAILURE
            return FailureMode.SERVICE_UNAVAILABLE
        
        elif category == EvidenceCategory.INTERNAL_SERVICE:
            # Check if imports are critical
            import_refs = [r for r in references if r.reference_type == ReferenceType.IMPORT]
            if any(r.criticality == Criticality.CRITICAL for r in import_refs):
                return FailureMode.BUILD_ERROR
            return FailureMode.RUNTIME_ERROR
        
        elif category == EvidenceCategory.EXTERNAL_DEPENDENCY:
            return FailureMode.BUILD_ERROR
        
        return FailureMode.UNKNOWN
    
    @staticmethod
    def extract_affected_systems(references: List[Reference]) -> List[str]:
        """
        Extract affected systems from references.
        
        Args:
            references: List of references
            
        Returns:
            List of affected system names
        """
        systems: Set[str] = set()
        
        for ref in references:
            # Add consumer if available
            if ref.consumer:
                systems.add(ref.consumer)
            
            # Add file path as a system identifier
            if ref.file_path:
                # Extract module/service name from file path
                parts = ref.file_path.replace('\\', '/').split('/')
                if len(parts) > 1:
                    # Use the top-level directory as system identifier
                    systems.add(parts[0])
        
        return sorted(list(systems))
    
    @staticmethod
    def extract_risk_drivers(references: List[Reference], category: EvidenceCategory) -> List[str]:
        """
        Extract risk drivers from references.
        
        Args:
            references: List of references
            category: Evidence category
            
        Returns:
            List of risk driver descriptions
        """
        drivers = []
        
        if not references:
            return drivers
        
        # Count by criticality
        critical_count = sum(1 for r in references if r.criticality == Criticality.CRITICAL)
        high_count = sum(1 for r in references if r.criticality == Criticality.HIGH)
        
        if critical_count > 0:
            drivers.append(f"{critical_count} critical dependencies that will cause immediate failures")
        
        if high_count > 0:
            drivers.append(f"{high_count} high-risk dependencies with significant impact")
        
        # Category-specific drivers
        if category == EvidenceCategory.RUNTIME:
            drivers.append("Runtime dependencies that will cause errors during execution")
        elif category == EvidenceCategory.CONFIGURATION:
            drivers.append("Configuration dependencies that may require environment updates")
        elif category == EvidenceCategory.INFRASTRUCTURE:
            drivers.append("Infrastructure dependencies that affect deployment")
        elif category == EvidenceCategory.DATABASE:
            drivers.append("Database dependencies that may require migration planning")
        elif category == EvidenceCategory.PUBLIC_API:
            drivers.append("Public API dependencies that affect external consumers")
        elif category == EvidenceCategory.INTERNAL_SERVICE:
            drivers.append("Internal service dependencies that may cause cascade failures")
        
        return drivers
