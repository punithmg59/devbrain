"""Reference Intelligence Engine - Runtime Analyzer."""

import ast
import json
import logging
import re
from pathlib import Path
from typing import List

from .base_analyzer import BaseAnalyzer
from .models import (
    Reference,
    ReferenceType,
    ReferenceLocation,
    Criticality
)

logger = logging.getLogger(__name__)


class RuntimeAnalyzer(BaseAnalyzer):
    """Analyzer for runtime references (FastAPI, Flask, Express routes)."""
    
    def __init__(self, config):
        super().__init__(config)
        self.route_patterns = {
            'fastapi': self._analyze_fastapi_routes,
            'flask': self._analyze_flask_routes,
            'express': self._analyze_express_routes,
        }
    
    async def analyze(self) -> List[Reference]:
        """Analyze runtime route definitions for references to the target entity."""
        references = []
        
        # Find all route definition files
        route_files = self._find_route_files()
        
        for file_path in route_files:
            file_references = await self._analyze_file(file_path)
            references.extend(file_references)
        
        logger.info(f"Runtime analysis found {len(references)} references")
        return references
    
    def _find_route_files(self) -> List[Path]:
        """Find all files that might contain route definitions."""
        route_files = []
        
        try:
            # Python files (FastAPI, Flask)
            route_files.extend(self.repo_path.rglob('*.py'))
            
            # JavaScript/TypeScript files (Express)
            route_files.extend(self.repo_path.rglob('*.js'))
            route_files.extend(self.repo_path.rglob('*.ts'))
            route_files.extend(self.repo_path.rglob('*.jsx'))
            route_files.extend(self.repo_path.rglob('*.tsx'))
            
        except Exception as e:
            logger.warning(f"Failed to find route files: {e}")
        
        return route_files
    
    async def _analyze_file(self, file_path: Path) -> List[Reference]:
        """Analyze a single file for route references."""
        references = []
        
        try:
            file_ext = file_path.sext.lower()
            relative_path = str(file_path.relative_to(self.repo_path))
            
            if file_ext == '.py':
                references = self._analyze_python_routes(file_path, relative_path)
            elif file_ext in {'.js', '.ts', '.jsx', '.tsx'}:
                references = self._analyze_javascript_routes(file_path, relative_path)
        
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
        
        return references
    
    def _analyze_python_routes(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze Python file for FastAPI/Flask routes."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Detect framework
            framework = self._detect_python_framework(content, tree)
            
            if framework == 'fastapi':
                references = self._analyze_fastapi_routes(file_path, relative_path, content, tree)
            elif framework == 'flask':
                references = self._analyze_flask_routes(file_path, relative_path, content, tree)
        
        except SyntaxError:
            # Fallback to regex-based analysis
            references = self._analyze_python_routes_fallback(file_path, relative_path)
        except Exception as e:
            logger.warning(f"Failed to analyze Python routes {file_path}: {e}")
        
        return references
    
    def _detect_python_framework(self, content: str, tree: ast.AST) -> str:
        """Detect which Python web framework is being used."""
        content_lower = content.lower()
        
        # Check imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if 'fastapi' in alias.name.lower():
                        return 'fastapi'
                    elif 'flask' in alias.name.lower():
                        return 'flask'
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if 'fastapi' in node.module.lower():
                        return 'fastapi'
                    elif 'flask' in node.module.lower():
                        return 'flask'
        
        # Check for common patterns
        if 'fastapi' in content_lower or '@app.' in content_lower:
            return 'fastapi'
        elif 'flask' in content_lower or 'Flask(' in content_lower:
            return 'flask'
        
        return None
    
    def _analyze_fastapi_routes(self, file_path: Path, relative_path: str, content: str, tree: ast.AST) -> List[Reference]:
        """Analyze FastAPI routes for references."""
        references = []
        
        for node in ast.walk(tree):
            # Check for @app.get, @app.post, etc. decorators
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    # Handle @app.get("/path")
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                                # Check if target name is in the route path or function
                                if self._matches_target(node.name):
                                    references.append(self._create_reference(
                                        ReferenceType.FASTAPI_ROUTE,
                                        relative_path,
                                        node.lineno,
                                        node.name,
                                        context=ast.get_source_segment(content, node)
                                    ))
                                
                                # Check route path string
                                for arg in decorator.args:
                                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                        if self._matches_target(arg.value):
                                            references.append(self._create_reference(
                                                ReferenceType.FASTAPI_ROUTE,
                                                relative_path,
                                                node.lineno,
                                                arg.value,
                                                context=ast.get_source_segment(content, decorator)
                                            ))
                    
                    # Handle @router.get, @router.post, etc.
                    elif isinstance(decorator, ast.Attribute):
                        if decorator.attr in ['get', 'post', 'put', 'delete', 'patch']:
                            if self._matches_target(node.name):
                                references.append(self._create_reference(
                                    ReferenceType.FASTAPI_ROUTE,
                                    relative_path,
                                    node.lineno,
                                    node.name,
                                    context=ast.get_source_segment(content, node)
                                ))
        
        return references
    
    def _analyze_flask_routes(self, file_path: Path, relative_path: str, content: str, tree: ast.AST) -> List[Reference]:
        """Analyze Flask routes for references."""
        references = []
        
        for node in ast.walk(tree):
            # Check for @app.route decorators
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr == 'route':
                                # Check if target name is in the function or route path
                                if self._matches_target(node.name):
                                    references.append(self._create_reference(
                                        ReferenceType.FLASK_ROUTE,
                                        relative_path,
                                        node.lineno,
                                        node.name,
                                        context=ast.get_source_segment(content, node)
                                    ))
                                
                                # Check route path string
                                for arg in decorator.args:
                                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                        if self._matches_target(arg.value):
                                            references.append(self._create_reference(
                                                ReferenceType.FLASK_ROUTE,
                                                relative_path,
                                                node.lineno,
                                                arg.value,
                                                context=ast.get_source_segment(content, decorator)
                                            ))
        
        return references
    
    def _analyze_python_routes_fallback(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Fallback regex-based analysis for Python routes."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            framework = None
            for line in lines:
                if 'fastapi' in line.lower():
                    framework = 'fastapi'
                    break
                elif 'flask' in line.lower():
                    framework = 'flask'
                    break
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                if framework == 'fastapi':
                    # FastAPI patterns
                    if re.search(rf'@.*\.(get|post|put|delete|patch)\(.*{re.escape(self.target_name)}', line):
                        references.append(self._create_reference(
                            ReferenceType.FASTAPI_ROUTE,
                            relative_path,
                            line_num,
                            self.target_name,
                            context=line
                        ))
                
                elif framework == 'flask':
                    # Flask patterns
                    if re.search(rf'@.*route\(.*{re.escape(self.target_name)}', line):
                        references.append(self._create_reference(
                            ReferenceType.FLASK_ROUTE,
                            relative_path,
                            line_num,
                            self.target_name,
                            context=line
                        ))
        
        except Exception as e:
            logger.warning(f"Failed to analyze Python routes fallback {file_path}: {e}")
        
        return references
    
    def _analyze_javascript_routes(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze JavaScript/TypeScript file for Express routes."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Express route patterns
                express_patterns = [
                    rf'\.(get|post|put|delete|patch)\(.*{re.escape(self.target_name)}',
                    rf'router\.(get|post|put|delete|patch)\(.*{re.escape(self.target_name)}',
                    rf'app\.(get|post|put|delete|patch)\(.*{re.escape(self.target_name)}',
                ]
                
                for pattern in express_patterns:
                    if re.search(pattern, line):
                        references.append(self._create_reference(
                            ReferenceType.EXPRESS_ROUTE,
                            relative_path,
                            line_num,
                            self.target_name,
                            context=line
                        ))
                        break  # Only add one reference per line
        
        except Exception as e:
            logger.warning(f"Failed to analyze JavaScript routes {file_path}: {e}")
        
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
            is_runtime=True
        )
        
        context_text, snippet = self._extract_context(file_path, line_number)
        
        return Reference(
            reference_type=ref_type,
            reference_location=ReferenceLocation.RUNTIME,
            file_path=file_path,
            line_number=line_number,
            confidence=0.9,  # Route analysis has high confidence
            criticality=criticality,
            provider=provider,
            context=context or context_text,
            snippet=snippet
        )
