"""Reference Intelligence Engine - Testing Analyzer."""

import ast
import logging
import re
from pathlib import Path
from typing import List
from xml.etree import ElementTree as ET

from .base_analyzer import BaseAnalyzer
from .models import (
    Reference,
    ReferenceType,
    ReferenceLocation,
    Criticality
)

logger = logging.getLogger(__name__)


class TestingAnalyzer(BaseAnalyzer):
    """Analyzer for test files (pytest, jest, junit)."""
    
    def __init__(self, config):
        super().__init__(config)
        self.test_directories = ['tests', 'test', '__tests__', 'spec']
    
    async def analyze(self) -> List[Reference]:
        """Analyze test files for references to the target entity."""
        references = []
        
        # Find all test files
        test_files = self._find_test_files()
        
        for file_path in test_files:
            file_references = await self._analyze_file(file_path)
            references.extend(file_references)
        
        logger.info(f"Testing analysis found {len(references)} references")
        return references
    
    def _find_test_files(self) -> List[Path]:
        """Find all test files in the repository."""
        test_files = []
        
        try:
            # Check for test directories
            for test_dir in self.test_directories:
                test_path = self.repo_path / test_dir
                if test_path.exists() and test_path.is_dir():
                    test_files.extend(test_path.rglob('*.py'))
                    test_files.extend(test_path.rglob('*.js'))
                    test_files.extend(test_path.rglob('*.ts'))
                    test_files.extend(test_path.rglob('*.jsx'))
                    test_files.extend(test_path.rglob('*.tsx'))
                    test_files.extend(test_path.rglob('*.xml'))
            
            # Also look for test files by naming pattern
            test_files.extend(self.repo_path.rglob('test_*.py'))
            test_files.extend(self.repo_path.rglob('*_test.py'))
            test_files.extend(self.repo_path.rglob('*.test.js'))
            test_files.extend(self.repo_path.rglob('*.test.ts'))
            test_files.extend(self.repo_path.rglob('*.spec.js'))
            test_files.extend(self.repo_path.rglob('*.spec.ts'))
            test_files.extend(self.repo_path.rglob('*.xml'))
            
        except Exception as e:
            logger.warning(f"Failed to find test files: {e}")
        
        return test_files
    
    async def _analyze_file(self, file_path: Path) -> List[Reference]:
        """Analyze a single test file for references."""
        references = []
        
        try:
            file_ext = file_path.suffix.lower()
            relative_path = str(file_path.relative_to(self.repo_path))
            
            if file_ext == '.py':
                references = self._analyze_pytest_file(file_path, relative_path)
            elif file_ext in {'.js', '.ts', '.jsx', '.tsx'}:
                references = self._analyze_jest_file(file_path, relative_path)
            elif file_ext == '.xml':
                references = self._analyze_junit_file(file_path, relative_path)
        
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
        
        return references
    
    def _analyze_pytest_file(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze pytest file for references."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # Check for test functions
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith('test_'):
                        # Check if target name is in function name or body
                        if self._matches_target(node.name):
                            references.append(self._create_reference(
                                ReferenceType.PYTEST_TEST,
                                relative_path,
                                node.lineno,
                                node.name,
                                context=ast.get_source_segment(content, node)
                            ))
                        
                        # Check function body for references
                        for child in ast.walk(node):
                            if isinstance(child, ast.Name):
                                if self._matches_target(child.id):
                                    references.append(self._create_reference(
                                        ReferenceType.PYTEST_TEST,
                                        relative_path,
                                        child.lineno,
                                        child.id,
                                        context=ast.get_source_segment(content, child)
                                    ))
                            elif isinstance(child, ast.Call):
                                if isinstance(child.func, ast.Name):
                                    if self._matches_target(child.func.id):
                                        references.append(self._create_reference(
                                            ReferenceType.PYTEST_TEST,
                                            relative_path,
                                            child.lineno,
                                            child.func.id,
                                            context=ast.get_source_segment(content, child)
                                        ))
                
                # Check for fixtures
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name):
                            if decorator.id == 'pytest.fixture':
                                if self._matches_target(node.name):
                                    references.append(self._create_reference(
                                        ReferenceType.PYTEST_TEST,
                                        relative_path,
                                        node.lineno,
                                        node.name,
                                        context=ast.get_source_segment(content, node)
                                    ))
        
        except SyntaxError:
            # Fallback to regex-based analysis
            references = self._analyze_pytest_fallback(file_path, relative_path)
        except Exception as e:
            logger.warning(f"Failed to analyze pytest file {file_path}: {e}")
        
        return references
    
    def _analyze_pytest_fallback(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Fallback regex-based analysis for pytest files."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Test function patterns
                if re.search(rf'def test_.*{re.escape(self.target_name)}', line):
                    references.append(self._create_reference(
                        ReferenceType.PYTEST_TEST,
                        relative_path,
                        line_num,
                        self.target_name,
                        context=line
                    ))
                
                # Fixture patterns
                if re.search(rf'@pytest.fixture.*{re.escape(self.target_name)}', line):
                    references.append(self._create_reference(
                        ReferenceType.PYTEST_TEST,
                        relative_path,
                        line_num,
                        self.target_name,
                        context=line
                    ))
                
                # Function call patterns
                if re.search(rf'\b{re.escape(self.target_name)}\s*\(', line):
                    references.append(self._create_reference(
                        ReferenceType.PYTEST_TEST,
                        relative_path,
                        line_num,
                        self.target_name,
                        context=line
                    ))
        
        except Exception as e:
            logger.warning(f"Failed to analyze pytest fallback {file_path}: {e}")
        
        return references
    
    def _analyze_jest_file(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze Jest file for references."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Test patterns (test(), it(), describe())
                jest_patterns = [
                    rf'test\(.*{re.escape(self.target_name)}',
                    rf'it\(.*{re.escape(self.target_name)}',
                    rf'describe\(.*{re.escape(self.target_name)}',
                ]
                
                for pattern in jest_patterns:
                    if re.search(pattern, line):
                        references.append(self._create_reference(
                            ReferenceType.JEST_TEST,
                            relative_path,
                            line_num,
                            self.target_name,
                            context=line
                        ))
                        break  # Only add one reference per line
                
                # Import patterns
                import_patterns = [
                    rf'import.*{re.escape(self.target_name)}',
                    rf'from.*{re.escape(self.target_name)}',
                    rf'require\(.*{re.escape(self.target_name)}',
                ]
                
                for pattern in import_patterns:
                    if re.search(pattern, line):
                        references.append(self._create_reference(
                            ReferenceType.JEST_TEST,
                            relative_path,
                            line_num,
                            self.target_name,
                            context=line
                        ))
                        break
                
                # Function call patterns
                if re.search(rf'\b{re.escape(self.target_name)}\s*\(', line):
                    references.append(self._create_reference(
                        ReferenceType.JEST_TEST,
                        relative_path,
                        line_num,
                        self.target_name,
                        context=line
                    ))
        
        except Exception as e:
            logger.warning(f"Failed to analyze Jest file {file_path}: {e}")
        
        return references
    
    def _analyze_junit_file(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze JUnit XML file for references."""
        references = []
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Search for target name in XML structure
            for elem in root.iter():
                # Check tag name
                if self._matches_target(elem.tag):
                    references.append(self._create_reference(
                        ReferenceType.JUNIT_TEST,
                        relative_path,
                        0,  # Line number not available in XML
                        elem.tag,
                        context=elem.tag
                    ))
                
                # Check attributes
                for attr_name, attr_value in elem.attrib.items():
                    if self._matches_target(attr_value):
                        references.append(self._create_reference(
                            ReferenceType.JUNIT_TEST,
                            relative_path,
                            0,
                            attr_value,
                            context=f"{attr_name}={attr_value}"
                        ))
                
                # Check text content
                if elem.text and self._matches_target(elem.text.strip()):
                    references.append(self._create_reference(
                        ReferenceType.JUNIT_TEST,
                        relative_path,
                        0,
                        elem.text.strip(),
                        context=elem.text.strip()
                    ))
        
        except ET.ParseError as e:
            logger.warning(f"Failed to parse JUnit XML file {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Failed to analyze JUnit file {file_path}: {e}")
        
        return references
    
    def _matches_target(self, text: str) -> bool:
        """Check if text matches the target entity."""
        # Exact match
        if text == self.target_name:
            return True
        
        # Case-insensitive match
        if text.lower() == self.target_name.lower():
            return True
        
        # Fuzzy match (contains target name)
        if self.target_name.lower() in text.lower():
            return True
        
        return False
    
    def _create_reference(
        self,
        ref_type: ReferenceType,
        file_path: str,
        line_number: int,
        provider: str,
        context: str
    ) -> Reference:
        """Create a Reference object."""
        criticality = self._calculate_criticality(
            ref_type.value,
            is_direct=True,
            is_runtime=False
        )
        
        context_text, snippet = self._extract_context(file_path, line_number)
        
        return Reference(
            reference_type=ref_type,
            reference_location=ReferenceLocation.TEST,
            file_path=file_path,
            line_number=line_number,
            confidence=0.85,  # Test analysis has high confidence
            criticality=criticality,
            provider=provider,
            context=context or context_text,
            snippet=snippet
        )
