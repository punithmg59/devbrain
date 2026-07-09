"""Reference Intelligence Engine - Infrastructure Analyzer."""

import logging
import re
from pathlib import Path
from typing import List

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from .base_analyzer import BaseAnalyzer
from .models import (
    Reference,
    ReferenceType,
    ReferenceLocation,
    Criticality
)

logger = logging.getLogger(__name__)


class InfrastructureAnalyzer(BaseAnalyzer):
    """Analyzer for infrastructure files (Docker, K8s, GitHub Actions)."""
    
    def __init__(self, config):
        super().__init__(config)
        self.infrastructure_patterns = {
            'Dockerfile': self._analyze_dockerfile,
            'docker-compose.yml': self._analyze_docker_compose,
            'docker-compose.yaml': self._analyze_docker_compose,
            '.github/workflows': self._analyze_github_actions,
            'k8s': self._analyze_kubernetes,
            'kubernetes': self._analyze_kubernetes,
            'deploy': self._analyze_kubernetes,
        }
    
    async def analyze(self) -> List[Reference]:
        """Analyze infrastructure files for references to the target entity."""
        references = []
        
        # Find all infrastructure files in the repository
        infra_files = self._find_infrastructure_files()
        
        for file_path in infra_files:
            file_references = await self._analyze_file(file_path)
            references.extend(file_references)
        
        logger.info(f"Infrastructure analysis found {len(references)} references")
        return references
    
    def _find_infrastructure_files(self) -> List[Path]:
        """Find all infrastructure files in the repository."""
        infra_files = []
        
        try:
            # Docker files
            infra_files.extend(self.repo_path.rglob('Dockerfile'))
            infra_files.extend(self.repo_path.rglob('docker-compose.yml'))
            infra_files.extend(self.repo_path.rglob('docker-compose.yaml'))
            
            # Kubernetes files
            infra_files.extend(self.repo_path.rglob('*.yaml'))  # Will filter later
            infra_files.extend(self.repo_path.rglob('*.yml'))
            
            # GitHub Actions
            infra_files.extend(self.repo_path.rglob('.github/workflows/*.yml'))
            infra_files.extend(self.repo_path.rglob('.github/workflows/*.yaml'))
            
        except Exception as e:
            logger.warning(f"Failed to find infrastructure files: {e}")
        
        return infra_files
    
    async def _analyze_file(self, file_path: Path) -> List[Reference]:
        """Analyze a single infrastructure file for references."""
        references = []
        
        try:
            file_name = file_path.name
            relative_path = str(file_path.relative_to(self.repo_path))
            
            # Determine file type and use appropriate analyzer
            if file_name == 'Dockerfile':
                references = self._analyze_dockerfile(file_path, relative_path)
            elif file_name in ['docker-compose.yml', 'docker-compose.yaml']:
                references = self._analyze_docker_compose(file_path, relative_path)
            elif '.github/workflows' in relative_path:
                references = self._analyze_github_actions(file_path, relative_path)
            elif self._is_kubernetes_file(file_path):
                references = self._analyze_kubernetes(file_path, relative_path)
            
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
        
        return references
    
    def _is_kubernetes_file(self, file_path: Path) -> bool:
        """Check if a file is likely a Kubernetes manifest."""
        file_name = file_path.name.lower()
        path_parts = file_path.parts
        
        # Check if in k8s or kubernetes directory
        if any('k8s' in p.lower() or 'kubernetes' in p.lower() or 'deploy' in p.lower() for p in path_parts):
            return True
        
        # Check for common K8s file patterns
        k8s_patterns = ['deployment', 'service', 'configmap', 'secret', 'ingress', 'statefulset', 'daemonset']
        if any(pattern in file_name for pattern in k8s_patterns):
            return True
        
        return False
    
    def _analyze_dockerfile(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze Dockerfile for references."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip comments
                if line.startswith('#'):
                    continue
                
                # Check for target name in various Dockerfile directives
                dockerfile_patterns = [
                    rf'FROM\s+.*{re.escape(self.target_name)}',
                    rf'COPY\s+.*{re.escape(self.target_name)}',
                    rf'ADD\s+.*{re.escape(self.target_name)}',
                    rf'RUN\s+.*{re.escape(self.target_name)}',
                    rf'ENV\s+.*{re.escape(self.target_name)}',
                    rf'ARG\s+.*{re.escape(self.target_name)}',
                    rf'CMD\s+.*{re.escape(self.target_name)}',
                    rf'ENTRYPOINT\s+.*{re.escape(self.target_name)}',
                ]
                
                for pattern in dockerfile_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        references.append(self._create_reference(
                            ReferenceType.DOCKERFILE,
                            relative_path,
                            line_num,
                            self.target_name,
                            context=line
                        ))
                        break  # Only add one reference per line
        
        except Exception as e:
            logger.warning(f"Failed to analyze Dockerfile {file_path}: {e}")
        
        return references
    
    def _analyze_docker_compose(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze docker-compose file for references."""
        references = []
        
        if not YAML_AVAILABLE:
            logger.warning("PyYAML not installed, skipping docker-compose analysis")
            return references
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Search for target name in docker-compose structure
            if isinstance(data, dict):
                # Check services
                if 'services' in data:
                    for service_name, service_config in data['services'].items():
                        if self._matches_target(service_name):
                            references.append(self._create_reference(
                                ReferenceType.DOCKER_COMPOSE,
                                relative_path,
                                0,
                                service_name,
                                context=f"service: {service_name}"
                            ))
                        
                        # Check service configuration
                        references.extend(self._search_dict_for_references(
                            service_config,
                            relative_path,
                            file_path,
                            ReferenceType.DOCKER_COMPOSE
                        ))
                
                # Check volumes
                if 'volumes' in data:
                    for volume_name in data['volumes']:
                        if self._matches_target(volume_name):
                            references.append(self._create_reference(
                                ReferenceType.DOCKER_COMPOSE,
                                relative_path,
                                0,
                                volume_name,
                                context=f"volume: {volume_name}"
                            ))
                
                # Check networks
                if 'networks' in data:
                    for network_name in data['networks']:
                        if self._matches_target(network_name):
                            references.append(self._create_reference(
                                ReferenceType.DOCKER_COMPOSE,
                                relative_path,
                                0,
                                network_name,
                                context=f"network: {network_name}"
                            ))
        
        except Exception as e:
            logger.warning(f"Failed to analyze docker-compose file {file_path}: {e}")
        
        return references
    
    def _analyze_github_actions(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze GitHub Actions workflow file for references."""
        references = []
        
        if not YAML_AVAILABLE:
            logger.warning("PyYAML not installed, skipping GitHub Actions analysis")
            return references
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Search for target name in GitHub Actions workflow
            references = self._search_dict_for_references(
                data,
                relative_path,
                file_path,
                ReferenceType.GITHUB_ACTIONS
            )
            
        except Exception as e:
            logger.warning(f"Failed to analyze GitHub Actions file {file_path}: {e}")
        
        return references
    
    def _analyze_kubernetes(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze Kubernetes manifest for references."""
        references = []
        
        if not YAML_AVAILABLE:
            logger.warning("PyYAML not installed, skipping Kubernetes analysis")
            return references
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load_all(f)
            
            # K8s files can have multiple documents
            if isinstance(data, list):
                for doc in data:
                    if doc:
                        references.extend(self._analyze_k8s_document(doc, relative_path, file_path))
            elif data:
                references.extend(self._analyze_k8s_document(data, relative_path, file_path))
        
        except Exception as e:
            logger.warning(f"Failed to analyze Kubernetes file {file_path}: {e}")
        
        return references
    
    def _analyze_k8s_document(self, data: dict, relative_path: str, file_path: Path) -> List[Reference]:
        """Analyze a single Kubernetes document."""
        references = []
        
        if not isinstance(data, dict):
            return references
        
        # Check common K8s fields
        k8s_fields = [
            'metadata.name',
            'metadata.labels',
            'metadata.annotations',
            'spec.selector.matchLabels',
            'spec.template.metadata.labels',
            'spec.serviceName',
            'spec.template.spec.serviceAccountName',
        ]
        
        for field in k8s_fields:
            keys = field.split('.')
            value = data
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break
            
            if value and self._matches_target(str(value)):
                references.append(self._create_reference(
                    ReferenceType.KUBERNETES,
                    relative_path,
                    0,
                    str(value),
                    context=f"{field}: {value}"
                ))
        
        # Recursively search entire document
        references.extend(self._search_dict_for_references(
            data,
            relative_path,
            file_path,
            ReferenceType.KUBERNETES
        ))
        
        return references
    
    def _search_dict_for_references(
        self,
        data: any,
        relative_path: str,
        file_path: Path,
        ref_type: ReferenceType
    ) -> List[Reference]:
        """Recursively search a dictionary/list structure for references."""
        references = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                # Check key
                if self._matches_target(str(key)):
                    references.append(self._create_reference(
                        ref_type,
                        relative_path,
                        0,
                        str(key),
                        context=str(key)
                    ))
                
                # Recurse into value
                references.extend(self._search_dict_for_references(
                    value, relative_path, file_path, ref_type
                ))
        
        elif isinstance(data, list):
            for item in data:
                references.extend(self._search_dict_for_references(
                    item, relative_path, file_path, ref_type
                ))
        
        elif isinstance(data, str):
            if self._matches_target(data):
                references.append(self._create_reference(
                    ref_type,
                    relative_path,
                    0,
                    data,
                    context=data
                ))
        
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
            reference_location=ReferenceLocation.INFRASTRUCTURE,
            file_path=file_path,
            line_number=line_number,
            confidence=0.7,  # Infrastructure analysis has moderate confidence
            criticality=criticality,
            provider=provider,
            context=context or context_text,
            snippet=snippet
        )
