"""
tests/test_call_graph_builder.py
---------------------------------
Unit tests for CallGraphBuilder — verifying node construction, edge deduplication,
weighting, adjacency list generation, and error tolerance.
"""

from models.call_models import CallRecord, CallType, FunctionCallDetectionResult
from models.symbol import Symbol, SymbolKind
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.call_graph.graph_builder import CallGraphBuilder


def _make_symbol(sym_id: str, fqn: str, name: str, kind=SymbolKind.FUNCTION, file_path="app.py"):
    return Symbol(
        id=sym_id,
        fqn=fqn,
        name=name,
        kind=kind,
        file_path=file_path,
    )


class TestCallGraphBuilder:
    def test_single_node_single_edge(self):
        sym_caller = _make_symbol("sym-caller", "app.auth", "auth")
        sym_callee = _make_symbol("sym-callee", "app.login", "login")
        sym_tab = SymbolTable(repository_id="repo1")
        sym_tab.add_symbol(sym_caller)
        sym_tab.add_symbol(sym_callee)

        call = CallRecord(
            caller_symbol_id="sym-caller",
            caller_fqn="app.auth",
            callee_symbol_id="sym-callee",
            callee_fqn="app.login",
            callee_name="login",
            file_path="app.py",
            line=5,
            column=4,
            call_type=CallType.FUNCTION,
        )

        det_result = FunctionCallDetectionResult(
            repository_id="repo1",
            calls={call.call_id: call},
        )

        builder = CallGraphBuilder(repository_id="repo1")
        res = builder.build_graph(det_result, sym_tab)

        assert res.graph.node_count == 2
        assert res.graph.edge_count == 1
        assert "sym-caller" in res.graph.nodes
        assert "sym-callee" in res.graph.nodes

        edge = list(res.graph.edges.values())[0]
        assert edge.caller_symbol_id == "sym-caller"
        assert edge.callee_symbol_id == "sym-callee"
        assert edge.weight == 1

        # Check Adjacency Lists
        assert res.graph.adjacency_list["sym-caller"] == ["sym-callee"]
        assert res.graph.reverse_adjacency_list["sym-callee"] == ["sym-caller"]

    def test_duplicate_edge_deduplication_and_weighting(self):
        """Two identical directed calls between caller and callee increase weight to 2."""
        sym_caller = _make_symbol("sym-caller", "app.auth", "auth")
        sym_callee = _make_symbol("sym-callee", "app.login", "login")
        sym_tab = SymbolTable(repository_id="repo1")
        sym_tab.add_symbol(sym_caller)
        sym_tab.add_symbol(sym_callee)

        c1 = CallRecord(
            caller_symbol_id="sym-caller",
            callee_symbol_id="sym-callee",
            callee_name="login",
            file_path="app.py",
            line=5,
            column=4,
        )
        c2 = CallRecord(
            caller_symbol_id="sym-caller",
            callee_symbol_id="sym-callee",
            callee_name="login",
            file_path="app.py",
            line=10,
            column=4,
        )

        det_result = FunctionCallDetectionResult(
            repository_id="repo1",
            calls={c1.call_id: c1, c2.call_id: c2},
        )

        builder = CallGraphBuilder(repository_id="repo1")
        res = builder.build_graph(det_result, sym_tab)

        assert res.graph.edge_count == 1
        assert res.metrics.duplicate_edges == 1
        edge = list(res.graph.edges.values())[0]
        assert edge.weight == 2

    def test_recursive_self_call(self):
        """foo -> foo self call."""
        sym_foo = _make_symbol("sym-foo", "math.factorial", "factorial")
        sym_tab = SymbolTable(repository_id="repo1")
        sym_tab.add_symbol(sym_foo)

        c1 = CallRecord(
            caller_symbol_id="sym-foo",
            callee_symbol_id="sym-foo",
            callee_name="factorial",
            file_path="math.py",
            line=8,
            column=12,
        )

        det_result = FunctionCallDetectionResult(repository_id="repo1", calls={c1.call_id: c1})
        builder = CallGraphBuilder(repository_id="repo1")
        res = builder.build_graph(det_result, sym_tab)

        assert res.graph.node_count == 1
        assert res.graph.edge_count == 1
        assert res.graph.adjacency_list["sym-foo"] == ["sym-foo"]
        assert res.graph.reverse_adjacency_list["sym-foo"] == ["sym-foo"]

    def test_mutual_recursion(self):
        """a -> b and b -> a."""
        sym_a = _make_symbol("sym-a", "pkg.is_even", "is_even")
        sym_b = _make_symbol("sym-b", "pkg.is_odd", "is_odd")
        sym_tab = SymbolTable(repository_id="repo1")
        sym_tab.add_symbol(sym_a)
        sym_tab.add_symbol(sym_b)

        c1 = CallRecord(caller_symbol_id="sym-a", callee_symbol_id="sym-b", callee_name="is_odd", file_path="pkg.py", line=2, column=4)
        c2 = CallRecord(caller_symbol_id="sym-b", callee_symbol_id="sym-a", callee_name="is_even", file_path="pkg.py", line=6, column=4)

        det_result = FunctionCallDetectionResult(repository_id="repo1", calls={c1.call_id: c1, c2.call_id: c2})
        res = CallGraphBuilder(repository_id="repo1").build_graph(det_result, sym_tab)

        assert res.graph.node_count == 2
        assert res.graph.edge_count == 2
        assert "sym-b" in res.graph.adjacency_list["sym-a"]
        assert "sym-a" in res.graph.adjacency_list["sym-b"]

    def test_external_call_synthesized_node(self):
        """Call to external / stdlib print() synthesizes an external node."""
        sym_caller = _make_symbol("sym-main", "app.main", "main")
        sym_tab = SymbolTable(repository_id="repo1")
        sym_tab.add_symbol(sym_caller)

        c1 = CallRecord(
            caller_symbol_id="sym-main",
            callee_symbol_id=None,
            callee_name="print",
            is_external=True,
            file_path="app.py",
            line=2,
            column=4,
        )

        det_result = FunctionCallDetectionResult(repository_id="repo1", calls={c1.call_id: c1})
        res = CallGraphBuilder(repository_id="repo1").build_graph(det_result, sym_tab)

        assert res.graph.node_count == 2
        assert res.graph.edge_count == 1
        assert "external:print" in res.graph.nodes
        assert res.graph.nodes["external:print"].is_external
        assert res.metrics.external_nodes == 1

    def test_missing_endpoint_skips_edge_gracefully(self):
        """Call record with missing caller and callee is skipped without crashing."""
        c1 = CallRecord(
            caller_symbol_id=None,
            callee_symbol_id=None,
            callee_name=None,
            file_path="bad.py",
            line=1,
            column=0,
        )
        det_result = FunctionCallDetectionResult(repository_id="repo1", calls={c1.call_id: c1})
        res = CallGraphBuilder(repository_id="repo1").build_graph(det_result)

        assert res.graph.edge_count == 0
        assert res.metrics.skipped_edges == 1
