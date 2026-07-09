"""Reference Intelligence Engine - Base Analyzer."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from .models import Reference, AnalyzerConfig, ReferenceLocation, Criticality

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """Base class for all reference analyzers."""
    
    def __init__(self, config: AnalyzerConfig):
        self.config = config
        self.repo_path = Path(config.repo_path)
        self.target_name = config.target_name
        self.target_id = config.target_id
        
    @abstractmethod
    async def analyze(self) -> List[Reference]:
        """
        Analyze references for the target entity.
        
        Returns:
            List of Reference objects
        """
        pass
    
    def _calculate_criticality(
        self,
        reference_type: str,
        is_direct: bool = True,
        is_runtime: bool = False
    ) -> Criticality:
        """
        Calculate criticality based on reference characteristics.
        
        Args:
            reference_type: Type of reference
            is_direct: Whether this is a direct reference
            is_runtime: Whether this is a runtime reference
            
        Returns:
            Criticality level
        """
        # Direct runtime references are most critical
        if is_direct and is_runtime:
            return Criticality.CRITICAL
        
        # Direct non-runtime references are high
        if is_direct:
            return Criticality.HIGH
        
        # Indirect runtime references are medium
        if is_runtime:
            return Criticality.MEDIUM
        
        # Indirect non-runtime references are low
        return Criticality.LOW
    
    def _extract_context(
        self,
        file_path: str,
        line_number: int,
        context_lines: int = 3
    ) -> tuple[str, str]:
        """
        Extract context and snippet from a file.
        
        Args:
            file_path: Path to the file
            line_number: Line number to extract context from
            context_lines: Number of lines before and after to include
            
        Returns:
            Tuple of (context, snippet)
        """
        try:
            full_path = self.repo_path / file_path
            if not full_path.exists():
                return "", ""
            
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Extract snippet (the line itself)
            if 0 < line_number <= len(lines):
                snippet = lines[line_number - 1].strip()
            else:
                snippet = ""
            
            # Extract context (lines around)
            start = max(0, line_number - context_lines - 1)
            end = min(len(lines), line_number + context_lines)
            context_lines_list = lines[start:end]
            context = ''.join(context_lines_list).strip()
            
            return context, snippet
            
        except Exception as e:
            logger.warning(f"Failed to extract context from {file_path}:{line_number}: {e}")
            return "", ""
    
    def _normalize_path(self, path: str) -> str:
        """Normalize a file path relative to repository root."""
        try:
            full_path = Path(path)
            if full_path.is_absolute():
                # Try to make it relative to repo
                try:
                    return str(full_path.relative_to(self.repo_path))
                except ValueError:
                    return path
            return path
        except Exception:
            return path
