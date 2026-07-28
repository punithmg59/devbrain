"""
tests/test_v2_analyzer_adapter.py
-----------------------------------
Production Unit & Integration Test for Repository Analyzer V2 Adapter.
"""

import os
import tempfile
from pathlib import Path
import pytest

from app.services.v2_analyzer_adapter import run_v2_analysis_collection, AnalysisPayloadV2


def test_v2_analysis_collection_on_sample_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = Path(tmpdir)
        
        # Create sample structure
        main_py = repo_dir / "main.py"
        main_py.write_text(
            "import os\n"
            "from utils import helper\n\n"
            "def main():\n"
            "    '''Main entry point.'''\n"
            "    res = helper()\n"
            "    return res\n",
            encoding="utf-8",
        )
        
        utils_dir = repo_dir / "utils"
        utils_dir.mkdir()
        utils_py = utils_dir / "helper.py"
        utils_py.write_text(
            "def helper():\n"
            "    '''Helper function.'''\n"
            "    return 'ok'\n",
            encoding="utf-8",
        )
        
        # Run V2 analysis collection
        payload: AnalysisPayloadV2 = run_v2_analysis_collection(str(repo_dir), "test-repo-123")
        print("PAYLOAD NODES:", payload.nodes)
        print("PAYLOAD EDGES:", payload.edges)
        
        assert payload.total_files == 2
        assert len(payload.files) == 2
        assert len(payload.folders) >= 1
        assert len(payload.nodes) >= 2  # files + functions
        
        # Check node types
        node_names = [n["name"] for n in payload.nodes]
        assert "main" in node_names
        assert "helper" in node_names
        
        # Check edges
        edge_types = [e["edge_type"] for e in payload.edges]
        assert "contains" in edge_types
