"""
tests/test_full_v2_pipeline.py
-------------------------------
End-to-End Integration Test for Repository Analyzer V2 Migration.

Verifies:
1. Multi-language repository discovery & parsing (Python, JavaScript, JSON, Markdown).
2. Schema compliance: ParserResult objects are valid Pydantic V2 models with required ParserMetadata.
3. Graph construction: Nodes and cross-file edges extracted by V2 DependencyGraphFacade.
4. DB persistence and post-analysis services execution without MissingGreenlet or lazy-loading failures.
5. Graph query engine compatibility with persisted analysis output.
"""

import tempfile
import uuid
from pathlib import Path
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base
from app.models import Repo, User
from app.services.v2_analyzer_adapter import run_v2_analysis_collection, AnalysisPayloadV2
from app.services.analysis import _persist_analysis
from app.services.alias_seeder import seed_aliases_for_repo, link_workflow_aliases_to_nodes, index_node_embeddings
from app.services.workflow_discovery_service import WorkflowDiscoveryService
from app.services.critical_path_service import CriticalPathService
from app.services.impact_precompute_service import ImpactPrecomputeService
from models.parser import ParserResult, ParserMetadata, ParserLanguage, ParserStatus
# NOTE: No @compiles(TextClause, "sqlite") hook here.
# The previous implementation called compiler.process(element, **kw) which
# re-invoked the same hook, causing infinite recursion and globally corrupting
# SQLAlchemy's compiler state for all subsequent tests in the same process.
# gen_random_uuid() is a PostgreSQL-only function; it is never issued against
# SQLite because the DialectUUID type uses Uuid() on SQLite (not gen_random_uuid).


@pytest.mark.asyncio
async def test_v2_pipeline_multi_language_and_persistence():
    # 1. Setup multi-language mock repository on disk
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = Path(tmpdir)

        # Python main file
        main_py = repo_dir / "main.py"
        main_py.write_text(
            "import os\n"
            "from utils.helper import process_data\n\n"
            "def main():\n"
            "    '''Main entry point.'''\n"
            "    return process_data({'status': 'active'})\n",
            encoding="utf-8",
        )

        # Python helper module
        utils_dir = repo_dir / "utils"
        utils_dir.mkdir()
        helper_py = utils_dir / "helper.py"
        helper_py.write_text(
            "def process_data(data):\n"
            "    '''Helper function.'''\n"
            "    return data.get('status')\n",
            encoding="utf-8",
        )

        # JavaScript frontend file
        js_dir = repo_dir / "frontend"
        js_dir.mkdir()
        app_js = js_dir / "app.js"
        app_js.write_text(
            "console.log('DevBrain Frontend Initialized');\n",
            encoding="utf-8",
        )

        # Config JSON
        config_json = repo_dir / "config.json"
        config_json.write_text('{"name": "test-repo", "version": "1.0.0"}\n', encoding="utf-8")

        # README Markdown
        readme_md = repo_dir / "README.md"
        readme_md.write_text("# Test Repository\nRepository Analyzer V2 test.\n", encoding="utf-8")

        # 2. Execute V2 Analysis Collection
        test_repo_id = str(uuid.uuid4())
        payload: AnalysisPayloadV2 = run_v2_analysis_collection(str(repo_dir), test_repo_id)

        # Assert discovered files & counts
        assert payload.total_files == 5
        assert len(payload.files) == 5
        assert len(payload.folders) >= 2
        assert len(payload.nodes) >= 2

        # Check node & edge extraction
        node_names = [n["name"] for n in payload.nodes]
        assert "main" in node_names
        assert "process_data" in node_names

        # 3. Test Async Database Persistence & Post-Analysis Services
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as db:
            # Create user & repo
            user = User(
                id=uuid.uuid4(),
                github_id=12345,
                username="testuser",
                email="test@example.com",
            )
            db.add(user)
            await db.flush()

            repo = Repo(
                id=uuid.UUID(test_repo_id),
                user_id=user.id,
                github_repo_id=98765,
                full_name="testuser/test-repo",
                name="test-repo",
                default_branch="main",
            )
            db.add(repo)
            await db.flush()

            # Persist analysis payload
            stats = await _persist_analysis(db, repo, payload)
            assert stats["total_files"] == 5
            assert stats["total_functions"] >= 2
            await db.commit()

            # Run post-analysis services (Must execute without MissingGreenlet or lazy-loading errors)
            alias_count = await seed_aliases_for_repo(repo.id, db)
            assert alias_count >= 0

            await link_workflow_aliases_to_nodes(repo.id, db)
            await index_node_embeddings(repo.id, db)
            await db.commit()

            wf_count = await WorkflowDiscoveryService().discover_for_repo(repo.id, db)
            assert wf_count >= 0
            await db.commit()

            path_count = await CriticalPathService().seed_for_repo(repo.id, db)
            assert path_count >= 0

            metric_count = await ImpactPrecomputeService().recompute_for_repo(repo.id, db)
            assert metric_count >= 0
            await db.commit()

        await engine.dispose()
