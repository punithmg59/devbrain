"""Reference Intelligence Engine - Database Analyzer."""

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


class DatabaseAnalyzer(BaseAnalyzer):
    """Analyzer for database references (migrations, ORM models, foreign keys)."""
    
    def __init__(self, config):
        super().__init__(config)
        self.migration_patterns = {
            'migrations': self._analyze_migrations_dir,
            'alembic': self._analyze_alembic_migrations,
            'migrate': self._analyze_migrations_dir,
        }
    
    async def analyze(self) -> List[Reference]:
        """Analyze database files for references to the target entity."""
        references = []
        
        # Find all database-related files
        db_files = self._find_database_files()
        
        for file_path in db_files:
            file_references = await self._analyze_file(file_path)
            references.extend(file_references)
        
        # Also analyze ORM models in source code
        orm_references = await self._analyze_orm_models()
        references.extend(orm_references)
        
        logger.info(f"Database analysis found {len(references)} references")
        return references
    
    def _find_database_files(self) -> List[Path]:
        """Find all database-related files in the repository."""
        db_files = []
        
        try:
            # Migration directories
            for pattern in self.migration_patterns.keys():
                db_files.extend(self.repo_path.rglob(pattern))
            
            # SQL files
            db_files.extend(self.repo_path.rglob('*.sql'))
            
            # Alembic versions
            db_files.extend(self.repo_path.rglob('alembic/versions/*.py'))
            
        except Exception as e:
            logger.warning(f"Failed to find database files: {e}")
        
        return db_files
    
    async def _analyze_file(self, file_path: Path) -> List[Reference]:
        """Analyze a single database file for references."""
        references = []
        
        try:
            file_ext = file_path.suffix.lower()
            relative_path = str(file_path.relative_to(self.repo_path))
            
            # SQL files
            if file_ext == '.sql':
                references = self._analyze_sql_file(file_path, relative_path)
            
            # Python migration files (alembic)
            elif file_ext == '.py':
                if 'alembic' in relative_path or 'migration' in relative_path.lower():
                    references = self._analyze_python_migration(file_path, relative_path)
            
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
        
        return references
    
    def _analyze_sql_file(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze SQL file for references."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip comments
                if line.startswith('--') or line.startswith('/*'):
                    continue
                
                # Check for table references
                sql_patterns = [
                    rf'CREATE TABLE.*{re.escape(self.target_name)}',
                    rf'ALTER TABLE.*{re.escape(self.target_name)}',
                    rf'DROP TABLE.*{re.escape(self.target_name)}',
                    rf'FROM\s+{re.escape(self.target_name)}',
                    rf'JOIN\s+{re.escape(self.target_name)}',
                    rf'INTO\s+{re.escape(self.target_name)}',
                    rf'UPDATE\s+{re.escape(self.target_name)}',
                    rf'DELETE FROM\s+{re.escape(self.target_name)}',
                    rf'FOREIGN KEY.*{re.escape(self.target_name)}',
                    rf'REFERENCES\s+{re.escape(self.target_name)}',
                    rf'CONSTRAINT.*{re.escape(self.target_name)}',
                ]
                
                for pattern in sql_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        ref_type = self._determine_sql_reference_type(line)
                        references.append(self._create_reference(
                            ref_type,
                            relative_path,
                            line_num,
                            self.target_name,
                            context=line
                        ))
                        break  # Only add one reference per line
        
        except Exception as e:
            logger.warning(f"Failed to analyze SQL file {file_path}: {e}")
        
        return references
    
    def _determine_sql_reference_type(self, line: str) -> ReferenceType:
        """Determine the type of SQL reference."""
        line_upper = line.upper()
        
        if 'FOREIGN KEY' in line_upper or 'REFERENCES' in line_upper:
            return ReferenceType.FOREIGN_KEY
        elif 'CREATE TABLE' in line_upper:
            return ReferenceType.SQL_MIGRATION
        else:
            return ReferenceType.SQL_MIGRATION
    
    def _analyze_python_migration(self, file_path: Path, relative_path: str) -> List[Reference]:
        """Analyze Python migration file (e.g., Alembic)."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Check for target name in migration code
                migration_patterns = [
                    rf'op\.create_table.*{re.escape(self.target_name)}',
                    rf'op\.drop_table.*{re.escape(self.target_name)}',
                    rf'op\.add_column.*{re.escape(self.target_name)}',
                    rf'op\.drop_column.*{re.escape(self.target_name)}',
                    rf'sa\.ForeignKey.*{re.escape(self.target_name)}',
                    rf'sa\.Column.*{re.escape(self.target_name)}',
                    rf'ForeignKey.*{re.escape(self.target_name)}',
                ]
                
                for pattern in migration_patterns:
                    if re.search(pattern, line):
                        ref_type = ReferenceType.SQL_MIGRATION
                        if 'ForeignKey' in line:
                            ref_type = ReferenceType.FOREIGN_KEY
                        
                        references.append(self._create_reference(
                            ref_type,
                            relative_path,
                            line_num,
                            self.target_name,
                            context=line
                        ))
                        break
        
        except Exception as e:
            logger.warning(f"Failed to analyze Python migration {file_path}: {e}")
        
        return references
    
    async def _analyze_orm_models(self) -> List[Reference]:
        """Analyze ORM models in source code for references."""
        references = []
        
        try:
            # Find Python files that might contain ORM models
            model_files = []
            for pattern in ['models.py', 'model.py', 'entities.py', 'entity.py']:
                model_files.extend(self.repo_path.rglob(pattern))
            
            for file_path in model_files:
                file_references = self._analyze_orm_file(file_path)
                references.extend(file_references)
        
        except Exception as e:
            logger.warning(f"Failed to analyze ORM models: {e}")
        
        return references
    
    def _analyze_orm_file(self, file_path: Path) -> List[Reference]:
        """Analyze a single ORM model file."""
        references = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            relative_path = str(file_path.relative_to(self.repo_path))
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Check for ORM patterns (SQLAlchemy, Django, etc.)
                orm_patterns = [
                    rf'class\s+{re.escape(self.target_name)}.*\(.*Model',
                    rf'class\s+{re.escape(self.target_name)}.*\(.*Base',
                    rf'ForeignKey.*{re.escape(self.target_name)}',
                    rf'relationship.*{re.escape(self.target_name)}',
                    rf'Column.*{re.escape(self.target_name)}',
                    rf'Field.*{re.escape(self.target_name)}',
                ]
                
                for pattern in orm_patterns:
                    if re.search(pattern, line):
                        ref_type = ReferenceType.ORM_MODEL
                        if 'ForeignKey' in line:
                            ref_type = ReferenceType.FOREIGN_KEY
                        
                        references.append(self._create_reference(
                            ref_type,
                            relative_path,
                            line_num,
                            self.target_name,
                            context=line
                        ))
                        break
        
        except Exception as e:
            logger.warning(f"Failed to analyze ORM file {file_path}: {e}")
        
        return references
    
    def _analyze_migrations_dir(self, file_path: Path) -> List[Reference]:
        """Analyze a migrations directory."""
        references = []
        
        try:
            if file_path.is_dir():
                for migration_file in file_path.glob('*.py'):
                    relative_path = str(migration_file.relative_to(self.repo_path))
                    file_references = self._analyze_python_migration(migration_file, relative_path)
                    references.extend(file_references)
        except Exception as e:
            logger.warning(f"Failed to analyze migrations directory {file_path}: {e}")
        
        return references
    
    def _analyze_alembic_migrations(self, file_path: Path) -> List[Reference]:
        """Analyze Alembic migrations."""
        references = []
        
        try:
            if file_path.is_dir():
                # Check for versions directory
                versions_dir = file_path / 'versions'
                if versions_dir.exists():
                    for migration_file in versions_dir.glob('*.py'):
                        relative_path = str(migration_file.relative_to(self.repo_path))
                        file_references = self._analyze_python_migration(migration_file, relative_path)
                        references.extend(file_references)
        except Exception as e:
            logger.warning(f"Failed to analyze Alembic migrations {file_path}: {e}")
        
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
            reference_location=ReferenceLocation.DATABASE,
            file_path=file_path,
            line_number=line_number,
            confidence=0.85,  # Database analysis has high confidence
            criticality=criticality,
            provider=provider,
            context=context or context_text,
            snippet=snippet
        )
