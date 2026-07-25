"""
tests/test_core_symbol_identity.py
-----------------------------------
Comprehensive unit test suite for Step 3.4 Symbol Identity Builder & CanonicalSymbolCollection.
"""

from typing import Any
import pytest
from pydantic import ValidationError

from core.namespaces import NamespaceBuilder
from core.symbol_extractor import RawSymbol, RawSymbolCollection, generate_temporary_id
from core.symbol_identity import (
    CANONICAL_SYMBOL_COLLECTION_VERSION,
    CanonicalSymbol,
    CanonicalSymbolCollection,
    SymbolIdentityBuilder,
    canonical_collection_to_dict,
    canonical_collection_to_json,
    dict_to_canonical_collection,
    generate_canonical_symbol_id,
    hash_canonical_collection,
    json_to_canonical_collection,
)
from core.symbols import (
    Language,
    NamespaceID,
    QualifiedName,
    SourceInformation,
    SourceLocation,
    SourceRange,
    SymbolID,
    SymbolKind,
)
from models.parser import ParserLanguage, ParserMetadata, ParserResult, ParserStatistics, ParserVersion


class TestCanonicalSymbol:
    def test_canonical_symbol_creation_and_fields(self):
        fqn = QualifiedName.from_string("repo.app.models.User")
        sym_id = generate_canonical_symbol_id("repo-1", Language.PYTHON, fqn, SymbolKind.CLASS)

        sym = CanonicalSymbol(
            id=sym_id,
            fqn=fqn,
            name="User",
            kind=SymbolKind.CLASS,
            namespace_id=NamespaceID(value="ns_123"),
            language=Language.PYTHON,
            repository_id="repo-1",
            file_id="file-1",
            file_path="app/models.py",
            source_info=SourceInformation(
                file_id="file-1",
                file_path="app/models.py",
                range=SourceRange(start=SourceLocation(line=1, column=0), end=SourceLocation(line=10, column=0))
            )
        )

        assert sym.name == "User"
        assert sym.kind == SymbolKind.CLASS
        assert sym.id.value.startswith("sym_")
        assert sym.fqn.to_string() == "repo.app.models.User"

    def test_canonical_symbol_immutability(self):
        fqn = QualifiedName.from_string("repo.app.models.User")
        sym_id = generate_canonical_symbol_id("repo-1", Language.PYTHON, fqn, SymbolKind.CLASS)

        sym = CanonicalSymbol(
            id=sym_id,
            fqn=fqn,
            name="User",
            kind=SymbolKind.CLASS,
            namespace_id=NamespaceID(value="ns_123"),
            language=Language.PYTHON,
            repository_id="repo-1",
            file_id="file-1",
            file_path="app/models.py",
            source_info=SourceInformation(
                file_id="file-1",
                file_path="app/models.py",
                range=SourceRange(start=SourceLocation(line=1, column=0), end=SourceLocation(line=10, column=0))
            )
        )

        with pytest.raises(ValidationError):
            sym.name = "NewUser"  # type: ignore


class TestSymbolIDAlgorithm:
    def test_deterministic_symbol_id_generation(self):
        id1 = generate_canonical_symbol_id("repo-123", Language.PYTHON, "app.models.User", SymbolKind.CLASS)
        id2 = generate_canonical_symbol_id("repo-123", "python", "app.models.User", "class")
        assert id1 == id2
        assert id1.value.startswith("sym_")

    def test_overload_discriminator_alters_symbol_id(self):
        id1 = generate_canonical_symbol_id("repo-123", Language.JAVA, "com.company.Auth.login", SymbolKind.METHOD)
        id2 = generate_canonical_symbol_id("repo-123", Language.JAVA, "com.company.Auth.login", SymbolKind.METHOD, overload_discriminator="overload_1")
        assert id1 != id2


class TestSymbolIdentityBuilderFacade:
    def create_sample_pipeline_inputs(self) -> tuple[RawSymbolCollection, Any]:
        ast_root = {
            "type": "module",
            "name": "service",
            "children": [
                {
                    "type": "class_def",
                    "name": "AuthService",
                    "range": {"start": {"line": 2, "column": 0}, "end": {"line": 15, "column": 0}},
                    "children": [
                        {
                            "type": "func_def",
                            "name": "login",
                            "range": {"start": {"line": 5, "column": 4}, "end": {"line": 10, "column": 4}}
                        }
                    ]
                }
            ]
        }

        pr = ParserResult(
            job_id="job-1",
            file_path="src/service.py",
            language=ParserLanguage.PYTHON,
            statistics=ParserStatistics(lines_parsed=20, node_count=5),
            metadata=ParserMetadata(parser_name="tree-sitter", language=ParserLanguage.PYTHON, version=ParserVersion(semver="1.0.0")),
            ast_root=ast_root
        )

        tree_builder = NamespaceBuilder()
        tree = tree_builder.build_tree([pr], repository_id="repo-devbrain")

        # Create RawSymbolCollection
        mod_node = tree.get_by_fqn("repo.src.service")
        assert mod_node is not None

        raw1 = RawSymbol(
            temp_id=generate_temporary_id("repo-devbrain", "src/service.py", mod_node.id, "AuthService", SymbolKind.CLASS, 1),
            kind=SymbolKind.CLASS,
            name="AuthService",
            qualified_name_candidate=mod_node.fqn.child("AuthService"),
            namespace_id=mod_node.id,
            language=Language.PYTHON,
            repository_id="repo-devbrain",
            file_id=pr.result_id,
            file_path="src/service.py",
            parser_result_id=pr.result_id,
            source_info=SourceInformation(
                file_id=pr.result_id,
                file_path="src/service.py",
                range=SourceRange(start=SourceLocation(line=2, column=0), end=SourceLocation(line=15, column=0))
            )
        )

        class_node = tree.get_by_fqn("repo.src.service.AuthService")
        assert class_node is not None

        raw2 = RawSymbol(
            temp_id=generate_temporary_id("repo-devbrain", "src/service.py", class_node.id, "login", SymbolKind.METHOD, 2),
            kind=SymbolKind.METHOD,
            name="login",
            qualified_name_candidate=class_node.fqn.child("login"),
            namespace_id=class_node.id,
            language=Language.PYTHON,
            repository_id="repo-devbrain",
            file_id=pr.result_id,
            file_path="src/service.py",
            parser_result_id=pr.result_id,
            source_info=SourceInformation(
                file_id=pr.result_id,
                file_path="src/service.py",
                range=SourceRange(start=SourceLocation(line=5, column=4), end=SourceLocation(line=10, column=4))
            )
        )

        raw_coll = RawSymbolCollection(
            repository_id="repo-devbrain",
            symbols=[raw1, raw2],
            symbols_by_file={"src/service.py": [raw1.temp_id, raw2.temp_id]}
        )

        return raw_coll, tree

    def test_build_canonical_symbols_end_to_end(self):
        raw_coll, tree = self.create_sample_pipeline_inputs()
        builder = SymbolIdentityBuilder()

        canonical_coll = builder.build_canonical_symbols(raw_coll, tree)

        assert canonical_coll.repository_id == "repo-devbrain"
        assert len(canonical_coll.symbols) == 2
        assert canonical_coll.statistics.total_canonical_symbols == 2

        # Verify class symbol lookup
        class_sym = canonical_coll.get_by_fqn("repo.src.service.AuthService")
        assert class_sym is not None
        assert class_sym.kind == SymbolKind.CLASS
        assert class_sym.id.value.startswith("sym_")

        # Verify method symbol lookup
        method_sym = canonical_coll.get_by_fqn("repo.src.service.AuthService.login")
        assert method_sym is not None
        assert method_sym.kind == SymbolKind.METHOD

        # Verify namespace index lookup
        class_ns_syms = canonical_coll.get_symbols_in_namespace(method_sym.namespace_id)
        assert len(class_ns_syms) == 1
        assert class_ns_syms[0].name == "login"


class TestSerialization:
    def test_json_roundtrip(self):
        raw_coll, tree = TestSymbolIdentityBuilderFacade().create_sample_pipeline_inputs()
        builder = SymbolIdentityBuilder()
        canonical_coll = builder.build_canonical_symbols(raw_coll, tree)

        json_str = canonical_collection_to_json(canonical_coll, indent=True)
        assert "_schema_version" in json_str

        reconstructed = json_to_canonical_collection(json_str, CanonicalSymbolCollection)
        assert reconstructed.repository_id == canonical_coll.repository_id
        assert len(reconstructed.symbols) == len(canonical_coll.symbols)

    def test_dict_roundtrip(self):
        raw_coll, tree = TestSymbolIdentityBuilderFacade().create_sample_pipeline_inputs()
        builder = SymbolIdentityBuilder()
        canonical_coll = builder.build_canonical_symbols(raw_coll, tree)

        d = canonical_collection_to_dict(canonical_coll)
        reconstructed = dict_to_canonical_collection(d, CanonicalSymbolCollection)
        assert reconstructed == canonical_coll

    def test_hash_canonical_collection(self):
        raw_coll, tree = TestSymbolIdentityBuilderFacade().create_sample_pipeline_inputs()
        builder = SymbolIdentityBuilder()
        canonical_coll = builder.build_canonical_symbols(raw_coll, tree)

        h1 = hash_canonical_collection(canonical_coll)
        h2 = hash_canonical_collection(canonical_coll)
        assert h1 == h2
        assert len(h1) == 64
