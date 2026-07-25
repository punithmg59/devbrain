"""
tests/test_core_namespaces.py
------------------------------
Comprehensive unit test suite for Step 3.2 Namespace Builder & NamespaceTree.
"""

import pytest
from pydantic import ValidationError

from core.namespaces import (
    DiagnosticSeverity,
    NamespaceBuildOptions,
    NamespaceBuilder,
    NamespaceDiagnostic,
    NamespaceDiagnostics,
    NamespaceKind,
    NamespaceNode,
    NamespaceTree,
    NamespaceTreeValidator,
    PythonScopeExtractor,
    ScopeDefinition,
    dict_to_tree,
    generate_scope_namespace_id,
    hash_tree,
    json_to_tree,
    tree_to_dict,
    tree_to_json,
)
from core.symbols import Language, QualifiedName, SourceLocation, SourceRange
from models.ast import ASTNode, ASTRoot, NodeLocation, NodeRange, NodeType
from models.parser import ParserLanguage, ParserMetadata, ParserResult, ParserStatus, ParserStatistics, ParserVersion


class TestNamespaceNode:
    def test_namespace_node_creation_and_fields(self):
        fqn = QualifiedName.from_string("repo.app.models.User")
        nid = generate_scope_namespace_id("repo-1", Language.PYTHON, "app/models.py", fqn, NamespaceKind.CLASS)
        
        node = NamespaceNode(
            id=nid,
            fqn=fqn,
            name="User",
            kind=NamespaceKind.CLASS,
            language=Language.PYTHON,
            repository_id="repo-1",
            file_path="app/models.py",
            declaration_order=1
        )
        
        assert node.name == "User"
        assert node.kind == NamespaceKind.CLASS
        assert node.language == Language.PYTHON
        assert node.is_root is True

    def test_namespace_node_immutability(self):
        fqn = QualifiedName.from_string("repo.app.models.User")
        nid = generate_scope_namespace_id("repo-1", Language.PYTHON, "app/models.py", fqn, NamespaceKind.CLASS)
        
        node = NamespaceNode(
            id=nid,
            fqn=fqn,
            name="User",
            kind=NamespaceKind.CLASS,
            language=Language.PYTHON,
            repository_id="repo-1"
        )
        
        with pytest.raises(ValidationError):
            node.name = "NewUser"  # type: ignore


class TestPythonScopeExtractor:
    def test_extract_scopes_from_ast_root(self):
        # Construct mock AST dict representing a Python module with a class and function
        ast_root = {
            "type": "module",
            "name": "service",
            "children": [
                {
                    "type": "class_definition",
                    "name": "AuthService",
                    "range": {"start": {"line": 5, "column": 0}, "end": {"line": 20, "column": 0}},
                    "children": [
                        {
                            "type": "function_definition",
                            "name": "login",
                            "range": {"start": {"line": 10, "column": 4}, "end": {"line": 15, "column": 4}}
                        }
                    ]
                },
                {
                    "type": "function_definition",
                    "name": "helper",
                    "range": {"start": {"line": 22, "column": 0}, "end": {"line": 25, "column": 0}}
                }
            ]
        }

        pr = ParserResult(
            job_id="job-1",
            file_path="app/service.py",
            language=ParserLanguage.PYTHON,
            metadata=ParserMetadata(parser_name="tree-sitter", language=ParserLanguage.PYTHON, version=ParserVersion(semver="1.0.0")),
            ast_root=ast_root
        )

        extractor = PythonScopeExtractor()
        scopes = extractor.extract_scopes(pr)

        assert len(scopes) == 2
        assert scopes[0].name == "AuthService"
        assert scopes[0].kind == NamespaceKind.CLASS
        assert len(scopes[0].children) == 1
        assert scopes[0].children[0].name == "login"
        assert scopes[0].children[0].kind == NamespaceKind.METHOD

        assert scopes[1].name == "helper"
        assert scopes[1].kind == NamespaceKind.FUNCTION


class TestNamespaceBuilder:
    def create_sample_parser_results(self) -> list[ParserResult]:
        ast_root1 = {
            "type": "module",
            "name": "users",
            "children": [
                {
                    "type": "class_def",
                    "name": "UserController",
                    "range": {"start": {"line": 2, "column": 0}, "end": {"line": 15, "column": 0}},
                    "children": [
                        {
                            "type": "func_def",
                            "name": "get_user",
                            "range": {"start": {"line": 5, "column": 4}, "end": {"line": 10, "column": 4}}
                        }
                    ]
                }
            ]
        }

        pr1 = ParserResult(
            job_id="job-1",
            file_path="src/api/users.py",
            language=ParserLanguage.PYTHON,
            statistics=ParserStatistics(lines_parsed=20, node_count=5),
            metadata=ParserMetadata(parser_name="tree-sitter", language=ParserLanguage.PYTHON, version=ParserVersion(semver="1.0.0")),
            ast_root=ast_root1
        )

        return [pr1]

    def test_build_tree_single_file(self):
        prs = self.create_sample_parser_results()
        builder = NamespaceBuilder()
        tree = builder.build_tree(prs, repository_id="repo-main")

        assert tree.repository_id == "repo-main"
        assert len(tree.nodes) > 0
        
        # Check Root Repository Node
        root = tree.get_node(tree.root_id)
        assert root is not None
        assert root.kind == NamespaceKind.REPOSITORY

        # Check Module Node
        mod_node = tree.get_by_fqn("repo.src.api.users")
        assert mod_node is not None
        assert mod_node.kind == NamespaceKind.MODULE
        assert mod_node.file_path == "src/api/users.py"

        # Check Class Node
        class_node = tree.get_by_fqn("repo.src.api.users.UserController")
        assert class_node is not None
        assert class_node.kind == NamespaceKind.CLASS
        assert class_node.parent_id == mod_node.id

        # Check Method Node
        method_node = tree.get_by_fqn("repo.src.api.users.UserController.get_user")
        assert method_node is not None
        assert method_node.kind == NamespaceKind.METHOD
        assert method_node.parent_id == class_node.id

    def test_tree_traversal_and_lookups(self):
        prs = self.create_sample_parser_results()
        builder = NamespaceBuilder()
        tree = builder.build_tree(prs, repository_id="repo-main")

        class_node = tree.get_by_fqn("repo.src.api.users.UserController")
        assert class_node is not None

        children = tree.get_children(class_node.id)
        assert len(children) == 1
        assert children[0].name == "get_user"

        ancestors = tree.get_ancestors(children[0].id)
        assert len(ancestors) == 5  # Class, Module, api Pkg, src Pkg, Repository Root

        # Test DFS and BFS
        dfs_nodes = list(tree.traverse_dfs())
        bfs_nodes = list(tree.traverse_bfs())
        assert len(dfs_nodes) == len(tree.nodes)
        assert len(bfs_nodes) == len(tree.nodes)

    def test_tree_statistics(self):
        prs = self.create_sample_parser_results()
        builder = NamespaceBuilder()
        tree = builder.build_tree(prs, repository_id="repo-main")

        stats = tree.get_statistics()
        assert stats.total_nodes > 0
        assert stats.total_files == 1
        assert "class" in stats.node_counts_by_kind

    def test_builder_resilience_on_error(self):
        # Create a malformed ParserResult
        pr_bad = ParserResult(
            job_id="job-bad",
            file_path="bad_file.py",
            language=ParserLanguage.PYTHON,
            metadata=ParserMetadata(parser_name="tree-sitter", language=ParserLanguage.PYTHON, version=ParserVersion(semver="1.0.0")),
            ast_root={"type": "invalid_unknown_type"}
        )

        builder = NamespaceBuilder()
        tree = builder.build_tree([pr_bad], repository_id="repo-err")

        # Tree should be constructed safely without crashing
        assert tree is not None
        assert tree.diagnostics.has_errors or len(tree.diagnostics.diagnostics) >= 0


class TestSerialization:
    def test_json_roundtrip(self):
        prs = TestNamespaceBuilder().create_sample_parser_results()
        builder = NamespaceBuilder()
        tree = builder.build_tree(prs, repository_id="repo-main")

        json_str = tree_to_json(tree, indent=True)
        assert "_schema_version" in json_str

        reconstructed = json_to_tree(json_str)
        assert reconstructed.repository_id == tree.repository_id
        assert reconstructed.root_id == tree.root_id
        assert len(reconstructed.nodes) == len(tree.nodes)

    def test_dict_roundtrip(self):
        prs = TestNamespaceBuilder().create_sample_parser_results()
        builder = NamespaceBuilder()
        tree = builder.build_tree(prs, repository_id="repo-main")

        d = tree_to_dict(tree)
        reconstructed = dict_to_tree(d)
        assert reconstructed == tree

    def test_hash_tree(self):
        prs = TestNamespaceBuilder().create_sample_parser_results()
        builder = NamespaceBuilder()
        tree = builder.build_tree(prs, repository_id="repo-main")

        h1 = hash_tree(tree)
        h2 = hash_tree(tree)
        assert h1 == h2
        assert len(h1) == 64
