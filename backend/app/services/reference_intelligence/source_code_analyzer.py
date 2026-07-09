"""Reference Intelligence Engine - Source Code Analyzer."""

import ast
import logging
import re
from pathlib import Path
from typing import List, Optional, Set

from .base_analyzer import BaseAnalyzer
from .models import (
    Reference,
    ReferenceType,
    ReferenceLocation,
    Criticality
)

logger = logging.getLogger(__name__)


class SourceCodeAnalyzer(BaseAnalyzer):
    """Analyzer for source code references (imports, calls, inheritance, etc.)."""
    
    def __init__(self, config):
        super().__init__(config)
        self.supported_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go'}
    
    async def analyze(self) -> List[Reference]:
        """Analyze source code for references to the target entity."""
        references = []
        
        # Find all source files in the repository
        source_files = self._find_source_files()
        
        for file_path in source_files:
            file_references = await self._analyze_file(file_path)
            references.extend(file_references)
        
        logger.info(f"Source code analysis found {len(references)} references")
        return references
    
    def _find_source_files(self) -> List[Path]:
        """Find all source code files in the repository."""
        source_files = []
        
        try:
            for ext in self.supported_extensions:
                source_files.extend(self.repo_path.rglob(f'*{ext}'))
        except Exception as e:
            logger.warning(f"Failed to find source files: {e}")
        
        return source_files
    
    async def _analyze_file(self, file_path: Path) -> List[Reference]:
        """Analyze a single source file for references."""
        references = []
        
        try:
            file_ext = file_path.suffix.lower()
            relative_path = str(file_path.relative_to(self.repo_path))
            
            if file_ext == '.py':
                references = self._analyze_python_file(file_path, relative_path)
            elif file_ext in {'.js', '.ts', '.jsx', '.tsx'}:
                references = self._analyze_javascript_file(file_path, relative_path)
            elif file_ext == '.java':
                references = self._analyze_java_file(file_path, relative_path)
            elif file_ext == '.go':
                references = self._analyze_go_file(file_path, relative_path)
            
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
        
        return references
    
    def _analyze_python_file(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze a Python file for references."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Track imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if self._matches_target(alias.name):
                            references.append(self._create_reference(
                                ReferenceType.IMPORT,
                                relative_path,
                                node.lineno,
                                alias.name,
                                context=ast.get_source_segment(content, node)
                            ))
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module and self._matches_target(node.module):
                        references.append(self._create_reference(
                            ReferenceType.IMPORT,
                            relative_path,
                            node.lineno,
                            node.module,
                            context=ast.get_source_segment(content, node)
                        ))
                    
                    for alias in node.names:
                        full_name = f"{node.module}.{alias.name}" if node.module else alias.name
                        if self._matches_target(full_name):
                            references.append(self._create_reference(
                                ReferenceType.IMPORT,
                                relative_path,
                                node.lineno,
                                full_name,
                                context=ast.get_source_segment(content, node)
                            ))
                
                # Track function calls
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if self._matches_target(node.func.id):
                            references.append(self._create_reference(
                                ReferenceType.FUNCTION_CALL,
                                relative_path,
                                node.lineno,
                                node.func.id,
                                context=ast.get_source_segment(content, node)
                            ))
                    elif isinstance(node.func, ast.Attribute):
                        if self._matches_target(node.func.attr):
                            references.append(self._create_reference(
                                ReferenceType.FUNCTION_CALL,
                                relative_path,
                                node.lineno,
                                node.func.attr,
                                context=ast.get_source_segment(content, node)
                            ))
                
                # Track class inheritance
                elif isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name) and self._matches_target(base.id):
                            references.append(self._create_reference(
                                ReferenceType.CLASS_INHERITANCE,
                                relative_path,
                                node.lineno,
                                base.id,
                                context=ast.get_source_segment(content, node)
                            ))
                
                # Track decorators
                elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name) and self._matches_target(decorator.id):
                            references.append(self._create_reference(
                                ReferenceType.DECORATOR,
                                relative_path,
                                node.lineno,
                                decorator.id,
                                context=ast.get_source_segment(content, node)
                            ))
                        elif isinstance(decorator, ast.Attribute) and self._matches_target(decorator.attr):
                            references.append(self._create_reference(
                                ReferenceType.DECORATOR,
                                relative_path,
                                node.lineno,
                                decorator.attr,
                                context=ast.get_source_segment(content, node)
                            ))
                
                # Track annotations
                elif isinstance(node, ast.AnnAssign):
                    if node.annotation:
                        annotation_str = ast.unparse(node.annotation)
                        if self._matches_target(annotation_str):
                            references.append(self._create_reference(
                                ReferenceType.ANNOTATION,
                                relative_path,
                                node.lineno,
                                annotation_str,
                                context=ast.get_source_segment(content, node)
                            ))
        
        except SyntaxError:
            # Try regex-based fallback for syntax errors
            references = self._analyze_python_fallback(content, relative_path)
        except Exception as e:
            logger.warning(f"Failed to parse Python file {file_path}: {e}")
        
        return references
    
    def _analyze_python_fallback(self, content: str, relative_path: str) -> List[Reference]:
        """Fallback regex-based analysis for Python files."""
        references = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Import patterns
            import_patterns = [
                rf'import\s+{re.escape(self.target_name)}',
                rf'from\s+.*{re.escape(self.target_name)}',
            ]
            
            for pattern in import_patterns:
                if re.search(pattern, line):
                    references.append(self._create_reference(
                        ReferenceType.IMPORT,
                        relative_path,
                        line_num,
                        self.target_name,
                        context=line.strip()
                    ))
            
            # Function call patterns
            if re.search(rf'\b{re.escape(self.target_name)}\s*\(', line):
                references.append(self._create_reference(
                    ReferenceType.FUNCTION_CALL,
                    relative_path,
                    line_num,
                    self.target_name,
                    context=line.strip()
                ))
        
        return references
    
    def _analyze_javascript_file(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze a JavaScript/TypeScript file for references."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Import patterns (ES6)
                import_patterns = [
                    rf'import.*{re.escape(self.target_name)}',
                    rf'from\s+[\'"].*{re.escape(self.target_name)}[\'"]',
                    rf'require\([\'"].*{re.escape(self.target_name)}[\'"]\)',
                ]
                
                for pattern in import_patterns:
                    if re.search(pattern, line):
                        references.append(self._create_reference(
                            ReferenceType.IMPORT,
                            relative_path,
                            line_num,
                            self.target_name,
                            context=line.strip()
                        ))
                
                # Function call patterns
                if re.search(rf'\b{re.escape(self.target_name)}\s*\(', line):
                    references.append(self._create_reference(
                        ReferenceType.FUNCTION_CALL,
                        relative_path,
                        line_num,
                        self.target_name,
                        context=line.strip()
                    ))
                
                # Class inheritance (extends)
                if re.search(rf'extends\s+{re.escape(self.target_name)}', line):
                    references.append(self._create_reference(
                        ReferenceType.CLASS_INHERITANCE,
                        relative_path,
                        line_num,
                        self.target_name,
                        context=line.strip()
                    ))
                
                # Decorator patterns (@decorator)
                if re.search(rf'@{re.escape(self.target_name)}', line):
                    references.append(self._create_reference(
                        ReferenceType.DECORATOR,
                        relative_path,
                        line_num,
                        self.target_name,
                        context=line.strip()
                    ))
        
        except Exception as e:
            logger.warning(f"Failed to analyze JavaScript file {file_path}: {e}")
        
        return references
    
    def _analyze_java_file(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze a Java file for references."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Import patterns
                if re.search(rf'import\s+.*{re.escape(self.target_name)}', line):
                    references.append(self._create_reference(
                        ReferenceType.IMPORT,
                        relative_path,
                        line_num,
                        self.target_name,
                        context=line.strip()
                    ))
                
                # Function call patterns
                if re.search(rf'\b{re.escape(self.target_name)}\s*\(', line):
                    references.append(self._create_reference(
                        ReferenceType.FUNCTION_CALL,
                        relative_path,
                        line_num,
                        self.target_name,
                        context=line.strip()
                    ))
                
                # Class inheritance (extends)
                if re.search(rf'extends\s+{re.escape(self.target_name)}', line):
                    references.append(self._create_reference(
                        ReferenceType.CLASS_INHERITANCE,
                        relative_path,
                        line_num,
                        self.target_name,
                        context=line.strip()
                    ))
                
                # Interface implementation (implements)
                if re.search(rf'implements\s+.*{re.escape(self.target_name)}', line):
                    references.append(self._create_reference(
                        ReferenceType.INTERFACE_IMPLEMENTATION,
                        relative_path,
                        line_num,
                        self.target_name,
                        context=line.strip()
                    ))
        
        except Exception as e:
            logger.warning(f"Failed to analyze Java file {file_path}: {e}")
        
        return references
    
    def _analyze_go_file(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze a Go file for references."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Import patterns
                if re.search(rf'import\s+.*{re.escape(self.target_name)}', line):
                    references.append(self._create_reference(
                        ReferenceType.IMPORT,
                        relative_path,
                        line_num,
                        self.target_name,
                        context=line.strip()
                    ))
                
                # Function call patterns
                if re.search(rf'\b{re.escape(self.target_name)}\s*\(', line):
                    references.append(self._create_reference(
                        ReferenceType.FUNCTION_CALL,
                        relative_path,
                        line_num,
                        self.target_name,
                        context=line.strip()
                    ))
        
        except Exception as e:
            logger.warning(f"Failed to analyze Go file {file_path}: {e}")
        
        return references
    
    def _matches_target(self, name: str) -> bool:
        """Check if a name matches the target entity."""
        # Exact match
        if name == self.target_name:
            return True
        
        # Module.submodule match (e.g., "services.auth.AuthService" matches "AuthService")
        if '.' in name:
            parts = name.split('.')
            if self.target_name in parts:
                return True
        
        # Case-insensitive match
        if name.lower() == self.target_name.lower():
            return True
        
        # Fuzzy match (contains target name)
        if self.target_name.lower() in name.lower():
            return True
        
        return False
    
    def _create_reference(
        self,
        ref_type: ReferenceType,
        file_path: str,
        line_number: int,
        provider: str,
        context: Optional[str] = None
    ) -> Reference:
        """Create a Reference object with calculated criticality."""
        is_direct = ref_type in {ReferenceType.IMPORT, ReferenceType.FUNCTION_CALL}
        is_runtime = ref_type in {ReferenceType.FUNCTION_CALL}
        
        criticality = self._calculate_criticality(
            ref_type.value,
            is_direct=is_direct,
            is_runtime=is_runtime
        )
        
        context_text, snippet = self._extract_context(file_path, line_number)
        
        return Reference(
            reference_type=ref_type,
            reference_location=ReferenceLocation.SOURCE_CODE,
            file_path=file_path,
            line_number=line_number,
            confidence=0.9,  # AST-based analysis has high confidence
            criticality=criticality,
            provider=provider,
            context=context or context_text,
            snippet=snippet
        )
