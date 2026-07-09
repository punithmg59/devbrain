"""Reference Intelligence Engine - Configuration Analyzer."""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    import toml
    TOML_AVAILABLE = True
except ImportError:
    TOML_AVAILABLE = False

from .base_analyzer import BaseAnalyzer
from .models import (
    Reference,
    ReferenceType,
    ReferenceLocation,
    Criticality
)

logger = logging.getLogger(__name__)


class ConfigurationAnalyzer(BaseAnalyzer):
    """Analyzer for configuration files (.env, yaml, json, toml, ini)."""
    
    def __init__(self, config):
        super().__init__(config)
        self.config_extensions = {
            '.env': self._analyze_env,
            '.yaml': self._analyze_yaml,
            '.yml': self._analyze_yaml,
            '.json': self._analyze_json,
            '.toml': self._analyze_toml,
            '.ini': self._analyze_ini,
            '.cfg': self._analyze_ini,
            '.conf': self._analyze_ini,
        }
    
    async def analyze(self) -> List[Reference]:
        """Analyze configuration files for references to the target entity."""
        references = []
        
        # Find all configuration files in the repository
        config_files = self._find_config_files()
        
        for file_path in config_files:
            file_references = await self._analyze_file(file_path)
            references.extend(file_references)
        
        logger.info(f"Configuration analysis found {len(references)} references")
        return references
    
    def _find_config_files(self) -> List[Path]:
        """Find all configuration files in the repository."""
        config_files = []
        
        try:
            for ext in self.config_extensions.keys():
                config_files.extend(self.repo_path.rglob(f'*{ext}'))
        except Exception as e:
            logger.warning(f"Failed to find config files: {e}")
        
        return config_files
    
    async def _analyze_file(self, file_path: Path) -> List[Reference]:
        """Analyze a single configuration file for references."""
        references = []
        
        try:
            file_ext = file_path.suffix.lower()
            relative_path = str(file_path.relative_to(self.repo_path))
            
            if file_ext in self.config_extensions:
                analyzer = self.config_extensions[file_ext]
                references = analyzer(file_path, relative_path)
            
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
        
        return references
    
    def _analyze_env(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze .env file for references."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip comments and empty lines
                if line.startswith('#') or not line:
                    continue
                
                # Check for key=value pattern
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    # Check if target name appears in key or value
                    if self._matches_target(key) or self._matches_target(value):
                        ref_type = ReferenceType.ENV_VAR
                        references.append(self._create_reference(
                            ref_type,
                            relative_path,
                            line_num,
                            key if self._matches_target(key) else value,
                            context=line
                        ))
        
        except Exception as e:
            logger.warning(f"Failed to analyze .env file {file_path}: {e}")
        
        return references
    
    def _analyze_yaml(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze YAML file for references."""
        references = []
        
        if not YAML_AVAILABLE:
            logger.warning("PyYAML not installed, skipping YAML analysis")
            return references
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                data = yaml.safe_load(content)
            
            # Recursively search for target name in YAML structure
            references = self._search_dict_for_references(
                data,
                relative_path,
                file_path,
                ReferenceType.YAML_CONFIG
            )
            
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML file {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Failed to analyze YAML file {file_path}: {e}")
        
        return references
    
    def _analyze_json(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze JSON file for references."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Recursively search for target name in JSON structure
            references = self._search_dict_for_references(
                data,
                relative_path,
                file_path,
                ReferenceType.JSON_CONFIG
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON file {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Failed to analyze JSON file {file_path}: {e}")
        
        return references
    
    def _analyze_toml(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze TOML file for references."""
        references = []
        
        if not TOML_AVAILABLE:
            logger.warning("toml not installed, skipping TOML analysis")
            return references
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = toml.load(f)
            
            # Recursively search for target name in TOML structure
            references = self._search_dict_for_references(
                data,
                relative_path,
                file_path,
                ReferenceType.TOML_CONFIG
            )
            
        except Exception as e:
            logger.warning(f"Failed to analyze TOML file {file_path}: {e}")
        
        return references
    
    def _analyze_ini(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze INI file for references."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip comments and empty lines
                if line.startswith('#') or line.startswith(';') or not line:
                    continue
                
                # Check for key=value pattern
                if '=' in line or ':' in line:
                    key, value = re.split(r'[=:]', line, 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    # Check if target name appears in key or value
                    if self._matches_target(key) or self._matches_target(value):
                        ref_type = ReferenceType.INI_CONFIG
                        references.append(self._create_reference(
                            ref_type,
                            relative_path,
                            line_num,
                            key if self._matches_target(key) else value,
                            context=line
                        ))
        
        except Exception as e:
            logger.warning(f"Failed to analyze INI file {file_path}: {e}")
        
        return references
    
    def _search_dict_for_references(
        self,
        data: Any,
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
                        0,  # Line number not available in parsed data
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
        
        # Snake/camel case conversion
        if self._convert_case(text) == self.target_name.lower():
            return True
        
        return False
    
    def _convert_case(self, text: str) -> str:
        """Convert text to snake_case for comparison."""
        # CamelCase to snake_case
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
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
            reference_location=ReferenceLocation.CONFIGURATION,
            file_path=file_path,
            line_number=line_number,
            confidence=0.8,  # Config analysis has moderate confidence
            criticality=criticality,
            provider=provider,
            context=context or context_text,
            snippet=snippet
        )
