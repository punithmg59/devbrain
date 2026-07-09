"""Unit tests for Reference Intelligence Engine."""

import pytest
from pathlib import Path
from uuid import UUID, uuid4

from app.services.reference_intelligence.models import (
    Reference,
    ReferenceType,
    ReferenceLocation,
    Criticality,
    ReferenceAnalysisResult,
    AnalyzerConfig
)
from app.services.reference_intelligence.reference_intelligence_engine import ReferenceIntelligenceEngine


class TestReferenceModels:
    """Test Reference Intelligence data models."""
    
    def test_reference_creation(self):
        """Test creating a Reference object."""
        reference = Reference(
            reference_type=ReferenceType.IMPORT,
            reference_location=ReferenceLocation.SOURCE_CODE,
            file_path="src/services/auth.py",
            line_number=10,
            confidence=0.9,
            criticality=Criticality.HIGH,
            provider="AuthService",
            context="from services.auth import AuthService",
            snippet="from services.auth import AuthService"
        )
        
        assert reference.reference_type == ReferenceType.IMPORT
        assert reference.file_path == "src/services/auth.py"
        assert reference.line_number == 10
        assert reference.confidence == 0.9
        assert reference.criticality == Criticality.HIGH
    
    def test_reference_analysis_result_metrics(self):
        """Test ReferenceAnalysisResult metric calculation."""
        result = ReferenceAnalysisResult(
            target_id=uuid4(),
            target_name="AuthService",
            target_type="service",
            repo_id=uuid4(),
            references=[
                Reference(
                    reference_type=ReferenceType.IMPORT,
                    reference_location=ReferenceLocation.SOURCE_CODE,
                    file_path="test.py",
                    line_number=1,
                    confidence=0.9,
                    criticality=Criticality.CRITICAL,
                    provider="AuthService"
                ),
                Reference(
                    reference_type=ReferenceType.FUNCTION_CALL,
                    reference_location=ReferenceLocation.SOURCE_CODE,
                    file_path="test.py",
                    line_number=5,
                    confidence=0.8,
                    criticality=Criticality.HIGH,
                    provider="AuthService"
                ),
            ]
        )
        
        result.calculate_metrics()
        
        assert result.total_references == 2
        assert result.critical_references == 1
        assert result.high_references == 1
        assert result.source_code_references == 2
        assert result.import_references == 1


class TestSourceCodeAnalyzer:
    """Test Source Code analyzer."""
    
    @pytest.fixture
    def sample_python_file(self, tmp_path):
        """Create a sample Python file for testing."""
        file_path = tmp_path / "test_service.py"
        file_path.write_text("""
from services.auth import AuthService
from services.user import UserService

class TestController:
    def __init__(self):
        self.auth = AuthService()
        self.user = UserService()
    
    def login(self):
        return self.auth.authenticate()
    
    def get_user(self):
        return self.user.get_user()
""")
        return file_path
    
    @pytest.mark.asyncio
    async def test_python_import_detection(self, sample_python_file):
        """Test Python import detection."""
        from app.services.reference_intelligence.source_code_analyzer import SourceCodeAnalyzer
        from app.services.reference_intelligence.models import AnalyzerConfig
        
        config = AnalyzerConfig(
            repo_id=uuid4(),
            repo_path=str(sample_python_file.parent),
            target_name="AuthService",
            target_id=uuid4(),
            target_type="service"
        )
        
        analyzer = SourceCodeAnalyzer(config)
        references = await analyzer.analyze()
        
        # Should find import of AuthService
        auth_imports = [r for r in references if r.provider == "AuthService"]
        assert len(auth_imports) > 0
        
        # Should find import reference type
        import_refs = [r for r in auth_imports if r.reference_type == ReferenceType.IMPORT]
        assert len(import_refs) > 0
    
    @pytest.mark.asyncio
    async def test_python_function_call_detection(self, sample_python_file):
        """Test Python function call detection."""
        from app.services.reference_intelligence.source_code_analyzer import SourceCodeAnalyzer
        from app.services.reference_intelligence.models import AnalyzerConfig
        
        config = AnalyzerConfig(
            repo_id=uuid4(),
            repo_path=str(sample_python_file.parent),
            target_name="authenticate",
            target_id=uuid4(),
            target_type="method"
        )
        
        analyzer = SourceCodeAnalyzer(config)
        references = await analyzer.analyze()
        
        # Should find function call to authenticate
        call_refs = [r for r in references if r.reference_type == ReferenceType.FUNCTION_CALL]
        assert len(call_refs) > 0


class TestConfigurationAnalyzer:
    """Test Configuration analyzer."""
    
    @pytest.fixture
    def sample_env_file(self, tmp_path):
        """Create a sample .env file for testing."""
        file_path = tmp_path / ".env"
        file_path.write_text("""
AUTH_SERVICE_URL=http://localhost:8000
DATABASE_URL=postgresql://localhost/mydb
AUTH_SERVICE_TIMEOUT=30
""")
        return file_path
    
    @pytest.mark.asyncio
    async def test_env_var_detection(self, sample_env_file):
        """Test .env variable detection."""
        from app.services.reference_intelligence.configuration_analyzer import ConfigurationAnalyzer
        from app.services.reference_intelligence.models import AnalyzerConfig
        
        config = AnalyzerConfig(
            repo_id=uuid4(),
            repo_path=str(sample_env_file.parent),
            target_name="AUTH_SERVICE",
            target_id=uuid4(),
            target_type="service"
        )
        
        analyzer = ConfigurationAnalyzer(config)
        references = await analyzer.analyze()
        
        # Should find references to AUTH_SERVICE in .env
        assert len(references) > 0
        
        # Should be ENV_VAR type
        env_refs = [r for r in references if r.reference_type == ReferenceType.ENV_VAR]
        assert len(env_refs) > 0


class TestDatabaseAnalyzer:
    """Test Database analyzer."""
    
    @pytest.fixture
    def sample_sql_file(self, tmp_path):
        """Create a sample SQL migration file for testing."""
        file_path = tmp_path / "migration.sql"
        file_path.write_text("""
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255)
);

ALTER TABLE orders ADD COLUMN user_id INTEGER REFERENCES users(id);

DROP TABLE IF EXISTS old_users;
""")
        return file_path
    
    @pytest.mark.asyncio
    async def test_sql_table_reference_detection(self, sample_sql_file):
        """Test SQL table reference detection."""
        from app.services.reference_intelligence.database_analyzer import DatabaseAnalyzer
        from app.services.reference_intelligence.models import AnalyzerConfig
        
        config = AnalyzerConfig(
            repo_id=uuid4(),
            repo_path=str(sample_sql_file.parent),
            target_name="users",
            target_id=uuid4(),
            target_type="table"
        )
        
        analyzer = DatabaseAnalyzer(config)
        references = await analyzer.analyze()
        
        # Should find references to users table
        assert len(references) > 0
        
        # Should be SQL_MIGRATION type
        sql_refs = [r for r in references if r.reference_type == ReferenceType.SQL_MIGRATION]
        assert len(sql_refs) > 0
    
    @pytest.mark.asyncio
    async def test_foreign_key_detection(self, sample_sql_file):
        """Test foreign key reference detection."""
        from app.services.reference_intelligence.database_analyzer import DatabaseAnalyzer
        from app.services.reference_intelligence.models import AnalyzerConfig
        
        config = AnalyzerConfig(
            repo_id=uuid4(),
            repo_path=str(sample_sql_file.parent),
            target_name="users",
            target_id=uuid4(),
            target_type="table"
        )
        
        analyzer = DatabaseAnalyzer(config)
        references = await analyzer.analyze()
        
        # Should find foreign key reference
        fk_refs = [r for r in references if r.reference_type == ReferenceType.FOREIGN_KEY]
        assert len(fk_refs) > 0


class TestRuntimeAnalyzer:
    """Test Runtime analyzer."""
    
    @pytest.fixture
    def sample_fastapi_file(self, tmp_path):
        """Create a sample FastAPI file for testing."""
        file_path = tmp_path / "routes.py"
        file_path.write_text("""
from fastapi import FastAPI

app = FastAPI()

@app.get("/auth/login")
async def login():
    return {"message": "login"}

@app.post("/auth/logout")
async def logout():
    return {"message": "logout"}
""")
        return file_path
    
    @pytest.mark.asyncio
    async def test_fastapi_route_detection(self, sample_fastapi_file):
        """Test FastAPI route detection."""
        from app.services.reference_intelligence.runtime_analyzer import RuntimeAnalyzer
        from app.services.reference_intelligence.models import AnalyzerConfig
        
        config = AnalyzerConfig(
            repo_id=uuid4(),
            repo_path=str(sample_fastapi_file.parent),
            target_name="login",
            target_id=uuid4(),
            target_type="function"
        )
        
        analyzer = RuntimeAnalyzer(config)
        references = await analyzer.analyze()
        
        # Should find route references
        assert len(references) > 0
        
        # Should be FASTAPI_ROUTE type
        route_refs = [r for r in references if r.reference_type == ReferenceType.FASTAPI_ROUTE]
        assert len(route_refs) > 0


class TestTestingAnalyzer:
    """Test Testing analyzer."""
    
    @pytest.fixture
    def sample_pytest_file(self, tmp_path):
        """Create a sample pytest file for testing."""
        file_path = tmp_path / "test_auth.py"
        file_path.write_text("""
import pytest
from services.auth import AuthService

def test_auth_service_login():
    auth = AuthService()
    result = auth.login()
    assert result is True

@pytest.fixture
def auth_service():
    return AuthService()
""")
        return file_path
    
    @pytest.mark.asyncio
    async def test_pytest_detection(self, sample_pytest_file):
        """Test pytest test detection."""
        from app.services.reference_intelligence.testing_analyzer import TestingAnalyzer
        from app.services.reference_intelligence.models import AnalyzerConfig
        
        config = AnalyzerConfig(
            repo_id=uuid4(),
            repo_path=str(sample_pytest_file.parent),
            target_name="AuthService",
            target_id=uuid4(),
            target_type="service"
        )
        
        analyzer = TestingAnalyzer(config)
        references = await analyzer.analyze()
        
        # Should find references in test file
        assert len(references) > 0
        
        # Should be PYTEST_TEST type
        test_refs = [r for r in references if r.reference_type == ReferenceType.PYTEST_TEST]
        assert len(test_refs) > 0


class TestReferenceIntelligenceEngine:
    """Test unified Reference Intelligence Engine orchestrator."""
    
    @pytest.fixture
    def sample_repo(self, tmp_path):
        """Create a sample repository structure for testing."""
        # Create directory structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        
        # Create source file
        (src_dir / "auth.py").write_text("""
class AuthService:
    def authenticate(self):
        return True
""")
        
        # Create test file
        (tests_dir / "test_auth.py").write_text("""
from src.auth import AuthService

def test_auth():
    auth = AuthService()
    assert auth.authenticate()
""")
        
        # Create .env file
        (tmp_path / ".env").write_text("AUTH_SERVICE_ENABLED=true")
        
        return tmp_path
    
    @pytest.mark.asyncio
    async def test_full_analysis(self, sample_repo):
        """Test full reference analysis across all analyzers."""
        engine = ReferenceIntelligenceEngine()
        
        result = await engine.analyze_references(
            repo_id=uuid4(),
            repo_path=str(sample_repo),
            target_name="AuthService",
            target_id=uuid4(),
            target_type="service",
            include_tests=True,
            include_infrastructure=False,
            include_configuration=True
        )
        
        # Should find references
        assert result.total_references > 0
        
        # Should have metrics calculated
        assert result.source_code_references >= 0
        assert result.test_references >= 0
        assert result.configuration_references >= 0
    
    @pytest.mark.asyncio
    async def test_delete_analysis(self, sample_repo):
        """Test DELETE-specific analysis."""
        engine = ReferenceIntelligenceEngine()
        
        result = await engine.analyze_for_delete(
            repo_id=uuid4(),
            repo_path=str(sample_repo),
            target_name="AuthService",
            target_id=uuid4(),
            target_type="service"
        )
        
        # DELETE analysis should focus on critical/high references
        for ref in result.references:
            assert ref.criticality.value in ['critical', 'high']
    
    @pytest.mark.asyncio
    async def test_rename_analysis(self, sample_repo):
        """Test RENAME-specific analysis."""
        engine = ReferenceIntelligenceEngine()
        
        result = await engine.analyze_for_rename(
            repo_id=uuid4(),
            repo_path=str(sample_repo),
            target_name="AuthService",
            target_id=uuid4(),
            target_type="service"
        )
        
        # RENAME analysis should focus on source code and configuration
        for ref in result.references:
            assert ref.reference_location.value in ['source_code', 'configuration']
    
    @pytest.mark.asyncio
    async def test_move_analysis(self, sample_repo):
        """Test MOVE-specific analysis."""
        engine = ReferenceIntelligenceEngine()
        
        result = await engine.analyze_for_move(
            repo_id=uuid4(),
            repo_path=str(sample_repo),
            target_name="AuthService",
            target_id=uuid4(),
            target_type="service"
        )
        
        # MOVE analysis should focus on imports
        for ref in result.references:
            assert ref.reference_type.value == 'import'


class TestCriticalityCalculation:
    """Test criticality calculation logic."""
    
    def test_direct_runtime_critical(self):
        """Test direct runtime references are critical."""
        from app.services.reference_intelligence.base_analyzer import BaseAnalyzer
        from app.services.reference_intelligence.models import AnalyzerConfig
        
        config = AnalyzerConfig(
            repo_id=uuid4(),
            repo_path="/tmp",
            target_name="test",
            target_id=uuid4(),
            target_type="service"
        )
        
        analyzer = BaseAnalyzer(config)
        criticality = analyzer._calculate_criticality(
            "function_call",
            is_direct=True,
            is_runtime=True
        )
        
        assert criticality == Criticality.CRITICAL
    
    def test_direct_non_runtime_high(self):
        """Test direct non-runtime references are high."""
        from app.services.reference_intelligence.base_analyzer import BaseAnalyzer
        from app.services.reference_intelligence.models import AnalyzerConfig
        
        config = AnalyzerConfig(
            repo_id=uuid4(),
            repo_path="/tmp",
            target_name="test",
            target_id=uuid4(),
            target_type="service"
        )
        
        analyzer = BaseAnalyzer(config)
        criticality = analyzer._calculate_criticality(
            "import",
            is_direct=True,
            is_runtime=False
        )
        
        assert criticality == Criticality.HIGH
    
    def test_indirect_runtime_medium(self):
        """Test indirect runtime references are medium."""
        from app.services.reference_intelligence.base_analyzer import BaseAnalyzer
        from app.services.reference_intelligence.models import AnalyzerConfig
        
        config = AnalyzerConfig(
            repo_id=uuid4(),
            repo_path="/tmp",
            target_name="test",
            target_id=uuid4(),
            target_type="service"
        )
        
        analyzer = BaseAnalyzer(config)
        criticality = analyzer._calculate_criticality(
            "function_call",
            is_direct=False,
            is_runtime=True
        )
        
        assert criticality == Criticality.MEDIUM


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
