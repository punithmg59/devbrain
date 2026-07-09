"""Reference Intelligence Engine - Unified Orchestrator."""

import logging
from pathlib import Path
from typing import List
from uuid import UUID

from .models import ReferenceAnalysisResult, AnalyzerConfig
from .source_code_analyzer import SourceCodeAnalyzer
from .configuration_analyzer import ConfigurationAnalyzer
from .infrastructure_analyzer import InfrastructureAnalyzer
from .database_analyzer import DatabaseAnalyzer
from .runtime_analyzer import RuntimeAnalyzer
from .testing_analyzer import TestingAnalyzer

logger = logging.getLogger(__name__)


class ReferenceIntelligenceEngine:
    """
    Unified Reference Intelligence Engine.
    
    This engine orchestrates all analyzers to find EVERY reference to a repository entity
    across source code, configuration, infrastructure, database, runtime, and testing.
    
    This is the single source of truth for:
    - DELETE operations (what breaks)
    - RENAME operations (what needs updating)
    - MOVE operations (import path changes)
    - Root Cause analysis (where is this used)
    - Simulation (cascade effects)
    """
    
    def __init__(self):
        self.analyzers = []
    
    async def analyze_references(
        self,
        repo_id: UUID,
        repo_path: str,
        target_name: str,
        target_id: UUID,
        target_type: str,
        max_depth: int = 5,
        include_tests: bool = True,
        include_infrastructure: bool = True,
        include_configuration: bool = True
    ) -> ReferenceAnalysisResult:
        """
        Analyze all references to a target entity in the repository.
        
        Args:
            repo_id: Repository UUID
            repo_path: Absolute path to repository
            target_name: Name of the target entity
            target_id: UUID of the target entity
            target_type: Type of the target entity
            max_depth: Maximum traversal depth
            include_tests: Whether to include test files
            include_infrastructure: Whether to include infrastructure files
            include_configuration: Whether to include configuration files
            
        Returns:
            ReferenceAnalysisResult with all references and metrics
        """
        config = AnalyzerConfig(
            repo_id=repo_id,
            repo_path=repo_path,
            target_name=target_name,
            target_id=target_id,
            target_type=target_type,
            max_depth=max_depth,
            include_tests=include_tests,
            include_infrastructure=include_infrastructure,
            include_configuration=include_configuration
        )
        
        # Initialize analyzers
        self.analyzers = [
            SourceCodeAnalyzer(config),
            ConfigurationAnalyzer(config),
            DatabaseAnalyzer(config),
            RuntimeAnalyzer(config),
        ]
        
        if include_tests:
            self.analyzers.append(TestingAnalyzer(config))
        
        if include_infrastructure:
            self.analyzers.append(InfrastructureAnalyzer(config))
        
        # Run all analyzers
        all_references = []
        for analyzer in self.analyzers:
            try:
                references = await analyzer.analyze()
                all_references.extend(references)
                logger.info(f"{analyzer.__class__.__name__} found {len(references)} references")
            except Exception as e:
                logger.error(f"Analyzer {analyzer.__class__.__name__} failed: {e}")
        
        # Create result
        result = ReferenceAnalysisResult(
            target_id=target_id,
            target_name=target_name,
            target_type=target_type,
            repo_id=repo_id,
            references=all_references
        )
        
        # Calculate metrics
        result.calculate_metrics()
        
        logger.info(f"Reference analysis complete: {result.total_references} total references")
        logger.info(f"  - Critical: {result.critical_references}")
        logger.info(f"  - High: {result.high_references}")
        logger.info(f"  - Medium: {result.medium_references}")
        logger.info(f"  - Low: {result.low_references}")
        
        return result
    
    async def analyze_for_delete(self, *args, **kwargs) -> ReferenceAnalysisResult:
        """
        Analyze references for DELETE operation.
        
        Focus on runtime failures and critical dependencies.
        """
        result = await self.analyze_references(*args, **kwargs)
        
        # Filter for critical and high references for DELETE
        result.references = [
            ref for ref in result.references
            if ref.criticality.value in ['critical', 'high']
        ]
        result.calculate_metrics()
        
        return result
    
    async def analyze_for_rename(self, *args, **kwargs) -> ReferenceAnalysisResult:
        """
        Analyze references for RENAME operation.
        
        Focus on imports, string references, and configuration.
        """
        result = await self.analyze_references(*args, **kwargs)
        
        # Prioritize source code and configuration for RENAME
        result.references = [
            ref for ref in result.references
            if ref.reference_location.value in ['source_code', 'configuration']
        ]
        result.calculate_metrics()
        
        return result
    
    async def analyze_for_move(self, *args, **kwargs) -> ReferenceAnalysisResult:
        """
        Analyze references for MOVE operation.
        
        Focus on imports and module dependencies.
        """
        result = await self.analyze_references(*args, **kwargs)
        
        # Focus on source code imports for MOVE
        result.references = [
            ref for ref in result.references
            if ref.reference_type.value == 'import'
        ]
        result.calculate_metrics()
        
        return result
    
    async def analyze_for_root_cause(self, *args, **kwargs) -> ReferenceAnalysisResult:
        """
        Analyze references for Root Cause analysis.
        
        Include all references for comprehensive analysis.
        """
        return await self.analyze_references(*args, **kwargs)
    
    async def analyze_for_simulation(self, *args, **kwargs) -> ReferenceAnalysisResult:
        """
        Analyze references for Simulation.
        
        Focus on runtime and critical references.
        """
        result = await self.analyze_references(*args, **kwargs)
        
        # Focus on runtime and critical references for simulation
        result.references = [
            ref for ref in result.references
            if ref.reference_location.value in ['runtime', 'source_code']
            and ref.criticality.value in ['critical', 'high']
        ]
        result.calculate_metrics()
        
        return result
