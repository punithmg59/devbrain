"""
tests/test_core_symbol_builder.py
----------------------------------
Comprehensive unit test suite for Step 3.6 Symbol Builder Facade & SemanticRepository.
"""

from typing import List
import pytest
from pydantic import ValidationError

from core.symbol_builder import (
    SEMANTIC_REPOSITORY_VERSION,
    SemanticRepository,
    SymbolBuilder,
    dict_to_semantic_repository,
    hash_semantic_repository,
    json_to_semantic_repository,
    semantic_repository_to_dict,
    semantic_repository_to_json,
)
from core.symbols import SymbolKind
from models.parser import ParserLanguage, ParserMetadata, ParserResult, ParserStatistics, ParserVersion


class TestSymbolBuilderFacade:
    def create_sample_parser_results(self) -> List[ParserResult]:
        ast1 = {
            "type": "module",
            "name": "models",
            "children": [
                {
                    "type": "class_def",
                    "name": "UserModel",
                    "range": {"start": {"line": 1, "column": 0}, "end": {"line": 10, "column": 0}},
                    "children": []
                }
            ]
        }

        pr1 = ParserResult(
            job_id="job-1",
            file_path="src/models.py",
            language=ParserLanguage.PYTHON,
            statistics=ParserStatistics(lines_parsed=10, node_count=3),
            metadata=ParserMetadata(parser_name="tree-sitter", language=ParserLanguage.PYTHON, version=ParserVersion(semver="1.0.0")),
            ast_root=ast1
        )

        ast2 = {
            "type": "module",
            "name": "views",
            "children": [
                {
                    "type": "func_def",
                    "name": "render_user",
                    "range": {"start": {"line": 1, "column": 0}, "end": {"line": 5, "column": 0}},
                    "children": []
                }
            ]
        }

        pr2 = ParserResult(
            job_id="job-2",
            file_path="src/views.py",
            language=ParserLanguage.PYTHON,
            statistics=ParserStatistics(lines_parsed=5, node_count=2),
            metadata=ParserMetadata(parser_name="tree-sitter", language=ParserLanguage.PYTHON, version=ParserVersion(semver="1.0.0")),
            ast_root=ast2
        )

        return [pr1, pr2]

    def test_end_to_end_symbol_builder_pipeline(self):
        results = self.create_sample_parser_results()

        repo = SymbolBuilder.build(
            workspace=None,
            parser_results=results,
            repository_id="repo-devbrain-36"
        )

        assert repo.repository_id == "repo-devbrain-36"
        assert repo.version == SEMANTIC_REPOSITORY_VERSION
        assert repo.is_valid()

        # Statistics verification
        stats = repo.statistics
        assert stats.total_files == 2
        assert stats.total_canonical_symbols == 2
        assert stats.total_indexed_symbols == 2
        assert "total_pipeline_ms" in stats.stage_timings_ms
        assert "namespace_builder_ms" in stats.stage_timings_ms
        assert "symbol_extractor_ms" in stats.stage_timings_ms
        assert "symbol_identity_ms" in stats.stage_timings_ms
        assert "symbol_table_ms" in stats.stage_timings_ms

        # Direct lookups on SemanticRepository
        fqns = sorted(list(repo.symbol_table.indexes.by_fqn.keys()))
        sym1 = repo.get_by_fqn(fqns[0])
        assert sym1 is not None
        
        sym2 = repo.get_by_fqn(fqns[1])
        assert sym2 is not None

        models_syms = repo.get_symbols_in_file("src/models.py")
        assert len(models_syms) == 1
        assert models_syms[0].name == "UserModel"

    def test_semantic_repository_immutability(self):
        results = self.create_sample_parser_results()
        repo = SymbolBuilder.build(parser_results=results, repository_id="repo-1")

        with pytest.raises(ValidationError):
            repo.repository_id = "new-repo"  # type: ignore


class TestSerialization:
    def test_json_roundtrip(self):
        results = TestSymbolBuilderFacade().create_sample_parser_results()
        repo = SymbolBuilder.build(parser_results=results, repository_id="repo-serialize")

        json_str = semantic_repository_to_json(repo, indent=True)
        assert "_schema_version" in json_str

        reconstructed = json_to_semantic_repository(json_str, SemanticRepository)
        assert reconstructed.repository_id == repo.repository_id
        assert reconstructed.statistics.total_canonical_symbols == repo.statistics.total_canonical_symbols

    def test_dict_roundtrip(self):
        results = TestSymbolBuilderFacade().create_sample_parser_results()
        repo = SymbolBuilder.build(parser_results=results, repository_id="repo-serialize")

        d = semantic_repository_to_dict(repo)
        reconstructed = dict_to_semantic_repository(d, SemanticRepository)
        assert reconstructed == repo

    def test_hash_semantic_repository(self):
        results = TestSymbolBuilderFacade().create_sample_parser_results()
        repo = SymbolBuilder.build(parser_results=results, repository_id="repo-serialize")

        h1 = hash_semantic_repository(repo)
        h2 = hash_semantic_repository(repo)
        assert h1 == h2
        assert len(h1) == 64
