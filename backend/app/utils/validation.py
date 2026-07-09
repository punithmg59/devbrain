"""
Validation utilities for DevBrain production readiness.

Provides validation for EngineeringEvidence objects and other critical data structures.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID

from app.services.engineering_evidence.models import EngineeringEvidence

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class EngineeringEvidenceValidator:
    """
    Validates EngineeringEvidence objects before reasoning.
    
    Ensures all evidence is grounded in repository data and meets quality thresholds.
    """
    
    # Minimum thresholds for evidence quality
    MIN_EVIDENCE_CONFIDENCE = 0.3
    MIN_AST_NODES = 0
    MIN_DEPENDENCY_EDGES = 0
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize the validator.
        
        Args:
            strict_mode: If True, raises exceptions on validation failures.
                        If False, logs warnings and returns validation result.
        """
        self.strict_mode = strict_mode
        logger.info(f"EngineeringEvidenceValidator initialized (strict_mode={strict_mode})")
    
    def validate(self, evidence: EngineeringEvidence) -> Dict[str, Any]:
        """
        Validate an EngineeringEvidence object.
        
        Args:
            evidence: The EngineeringEvidence object to validate
            
        Returns:
            Dictionary with validation results:
            - is_valid: bool
            - errors: List of error messages
            - warnings: List of warning messages
            - confidence_score: float
            
        Raises:
            ValidationError: If validation fails in strict mode
        """
        logger.info(f"Validating EngineeringEvidence for target={evidence.target_name}")
        
        errors = []
        warnings = []
        
        # Validate required fields
        self._validate_required_fields(evidence, errors)
        
        # Validate evidence confidence
        self._validate_evidence_confidence(evidence, errors, warnings)
        
        # Validate AST nodes
        self._validate_ast_nodes(evidence, warnings)
        
        # Validate dependency graph
        self._validate_dependency_graph(evidence, warnings)
        
        # Validate call graph
        self._validate_call_graph(evidence, warnings)
        
        # Validate classes and functions
        self._validate_entities(evidence, warnings)
        
        # Validate data completeness
        self._validate_data_completeness(evidence, errors, warnings)
        
        # Calculate overall confidence score
        confidence_score = self._calculate_confidence_score(evidence, errors, warnings)
        
        is_valid = len(errors) == 0
        
        validation_result = {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "confidence_score": confidence_score
        }
        
        # Log validation result
        if is_valid:
            logger.info(f"Validation passed: confidence={confidence_score:.2f}, warnings={len(warnings)}")
        else:
            logger.error(f"Validation failed: {len(errors)} errors, {len(warnings)} warnings")
            for error in errors:
                logger.error(f"  - {error}")
        
        # Raise exception in strict mode if invalid
        if self.strict_mode and not is_valid:
            raise ValidationError(f"EngineeringEvidence validation failed: {errors}")
        
        return validation_result
    
    def _validate_required_fields(self, evidence: EngineeringEvidence, errors: List[str]):
        """Validate required fields are present."""
        required_fields = ['target_id', 'target_name', 'target_type', 'repo_id']
        
        for field in required_fields:
            if not hasattr(evidence, field) or getattr(evidence, field) is None:
                errors.append(f"Missing required field: {field}")
    
    def _validate_evidence_confidence(self, evidence: EngineeringEvidence, errors: List[str], warnings: List[str]):
        """Validate evidence confidence threshold."""
        if evidence.evidence_confidence < self.MIN_EVIDENCE_CONFIDENCE:
            errors.append(
                f"Evidence confidence {evidence.evidence_confidence:.2f} below threshold {self.MIN_EVIDENCE_CONFIDENCE}"
            )
        elif evidence.evidence_confidence < 0.5:
            warnings.append(f"Low evidence confidence: {evidence.evidence_confidence:.2f}")
    
    def _validate_ast_nodes(self, evidence: EngineeringEvidence, warnings: List[str]):
        """Validate AST nodes."""
        if len(evidence.ast_nodes) < self.MIN_AST_NODES:
            warnings.append(f"Low AST node count: {len(evidence.ast_nodes)}")
        
        # Check for malformed AST nodes
        for node in evidence.ast_nodes:
            if not node.name or not node.file_path:
                warnings.append(f"Malformed AST node: missing name or file_path")
    
    def _validate_dependency_graph(self, evidence: EngineeringEvidence, warnings: List[str]):
        """Validate dependency graph."""
        if evidence.dependency_graph:
            if evidence.dependency_graph.total_edges < self.MIN_DEPENDENCY_EDGES:
                warnings.append(f"Low dependency edge count: {evidence.dependency_graph.total_edges}")
            
            # Check for self-referencing dependencies
            for edge in evidence.dependency_graph.edges:
                if edge.from_node == edge.to_node:
                    warnings.append(f"Self-referencing dependency: {edge.from_node}")
        else:
            warnings.append("Missing dependency graph")
    
    def _validate_call_graph(self, evidence: EngineeringEvidence, warnings: List[str]):
        """Validate call graph."""
        if evidence.call_graph:
            if len(evidence.call_graph.function_calls) == 0:
                warnings.append("Empty call graph")
        else:
            warnings.append("Missing call graph")
    
    def _validate_entities(self, evidence: EngineeringEvidence, warnings: List[str]):
        """Validate classes and functions."""
        if len(evidence.classes) == 0 and len(evidence.functions) == 0:
            warnings.append("No classes or functions found in evidence")
    
    def _validate_data_completeness(self, evidence: EngineeringEvidence, errors: List[str], warnings: List[str]):
        """Validate data completeness scores."""
        if not evidence.data_completeness:
            errors.append("Missing data completeness information")
            return
        
        for data_type, score in evidence.data_completeness.items():
            if score < 0.0 or score > 1.0:
                errors.append(f"Invalid completeness score for {data_type}: {score}")
            elif score < 0.3:
                warnings.append(f"Low completeness for {data_type}: {score:.2f}")
    
    def _calculate_confidence_score(self, evidence: EngineeringEvidence, errors: List[str], warnings: List[str]) -> float:
        """
        Calculate overall confidence score based on validation results.
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_score = evidence.evidence_confidence
        
        # Penalize for errors
        error_penalty = len(errors) * 0.1
        warning_penalty = len(warnings) * 0.02
        
        final_score = max(0.0, base_score - error_penalty - warning_penalty)
        
        return final_score


def validate_engineering_evidence(evidence: EngineeringEvidence, strict: bool = False) -> Dict[str, Any]:
    """
    Convenience function to validate EngineeringEvidence.
    
    Args:
        evidence: The EngineeringEvidence object to validate
        strict: Whether to raise exceptions on validation failure
        
    Returns:
        Validation result dictionary
    """
    validator = EngineeringEvidenceValidator(strict_mode=strict)
    return validator.validate(evidence)
