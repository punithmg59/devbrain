"""
tests/test_regression_validator.py
-----------------------------------
Unit tests for RegressionValidator — verifying 12-point pipeline regression checks.
"""

from analysis.benchmark.regression_validator import RegressionValidator
from models.benchmark_models import RegressionStatus


class TestRegressionValidator:
    def test_regression_validator_passes_on_valid_data(self):
        pipeline_data = {
            "discovery": [type("File", (), {"file_path": "app.py"})()],
            "parse_result": type("ParseRes", (), {"failed_parses": 0})(),
            "semantic_results": [
                type("SemRes", (), {"module": type("Mod", (), {"functions": [1], "classes": [1]})()})()
            ],
            "symbol_table": type("SymTab", (), {"symbols": {"s1": 1}})(),
            "scope_result": type("ScopeRes", (), {"scopes": {"sc1": 1}})(),
            "import_result": type("ImpRes", (), {"metrics": type("M", (), {"resolved_imports": 5})()})(),
            "reference_result": type("RefRes", (), {"metrics": type("M", (), {"resolved_references": 10})()})(),
            "call_detection_result": type("CallDet", (), {"metrics": type("M", (), {"total_calls": 8})()})(),
            "call_graph_result": type("CGRes", (), {"graph": type("G", (), {"node_count": 5, "edge_count": 4})()})(),
            "graph_index_result": type("IdxRes", (), {"metrics": type("M", (), {"indexed_nodes": 5, "indexed_edges": 4})()})(),
            "graph_validation_result": type("ValRes", (), {"validation_report": type("R", (), {"is_valid": True})()})(),
            "processing_result": type("ProcRes", (), {"success": True})(),
        }

        validator = RegressionValidator()
        report = validator.validate_pipeline_results(pipeline_data)

        assert report.overall_status == RegressionStatus.PASS
        assert report.failure_count == 0
        assert len(report.checks) == 12
