"""
tests/test_core_symbols.py
---------------------------
Comprehensive unit test suite for Step 3.1 Canonical Symbol Model.
"""

import json
import pytest
from pydantic import ValidationError

from core.symbols import (
    Accessibility,
    AccessibilityKind,
    Annotation,
    Attribute,
    Documentation,
    DocumentationFormat,
    GenericParameter,
    Language,
    Metadata,
    ModifierKind,
    ModifierSet,
    NamespaceID,
    OriginKind,
    QualifiedName,
    QualifiedNameError,
    RelationshipKind,
    SourceInformation,
    SourceLocation,
    SourceRange,
    Symbol,
    SymbolID,
    ISymbol,
    ISymbolID,
    SymbolIDError,
    SymbolKind,
    SymbolOrigin,
    SymbolOwner,
    SymbolRelationship,
    SymbolSerializationError,
    SymbolValidationError,
    SymbolVersion,
    TypeReference,
    VarianceKind,
    Visibility,
    VisibilityKind,
    are_symbols_equal,
    dict_to_symbol,
    generate_namespace_id,
    generate_symbol_id,
    hash_symbol,
    json_to_symbol,
    symbol_to_dict,
    symbol_to_json,
)


class TestQualifiedName:
    def test_qualified_name_from_string_dot(self):
        qn = QualifiedName.from_string("com.company.project.service.AuthService.login")
        assert qn.name == "login"
        assert len(qn.segments) == 6
        assert qn.parent.name == "AuthService"
        assert qn.to_string() == "com.company.project.service.AuthService.login"

    def test_qualified_name_from_string_colon(self):
        qn = QualifiedName.from_string("std::collections::HashMap::insert", separator="::")
        assert qn.name == "insert"
        assert qn.parent.to_string("::") == "std::collections::HashMap"

    def test_qualified_name_child_and_parent(self):
        root = QualifiedName.from_string("app")
        assert root.is_root
        assert root.parent is None
        
        child1 = root.child("api")
        assert not child1.is_root
        assert child1.to_string() == "app.api"
        assert child1.parent == root

    def test_qualified_name_empty_raises(self):
        with pytest.raises(QualifiedNameError):
            QualifiedName.from_string("")

        with pytest.raises(QualifiedNameError):
            QualifiedName.from_string("   ")


class TestSymbolID:
    def test_deterministic_symbol_id(self):
        id1 = generate_symbol_id("repo-123", Language.PYTHON, "app.models.User", SymbolKind.CLASS)
        id2 = generate_symbol_id("repo-123", "python", "app.models.User", "class")
        assert id1 == id2
        assert id1.value.startswith("sym_")

    def test_different_inputs_produce_different_ids(self):
        id1 = generate_symbol_id("repo-123", Language.PYTHON, "app.models.User", SymbolKind.CLASS)
        id2 = generate_symbol_id("repo-456", Language.PYTHON, "app.models.User", SymbolKind.CLASS)
        id3 = generate_symbol_id("repo-123", Language.PYTHON, "app.models.User", SymbolKind.FUNCTION)
        assert id1 != id2
        assert id1 != id3

    def test_invalid_symbol_id_format(self):
        with pytest.raises(SymbolIDError):
            SymbolID(value="invalid_prefix_123")


class TestSymbolKindsAndEnums:
    def test_all_28_minimum_symbol_kinds_supported(self):
        expected_kinds = [
            "module", "package", "namespace", "class", "interface", "struct",
            "enum", "trait", "protocol", "record", "union", "function", "method",
            "constructor", "destructor", "property", "field", "variable", "constant",
            "parameter", "type_alias", "generic_parameter", "decorator", "annotation",
            "macro", "import", "export", "unknown"
        ]
        for kind_str in expected_kinds:
            kind_enum = SymbolKind(kind_str)
            assert kind_enum.value == kind_str


class TestModifiers:
    def test_modifier_set_queries(self):
        mods = ModifierSet(modifiers=[ModifierKind.STATIC, ModifierKind.ASYNC, "abstract"])
        assert mods.is_static
        assert mods.is_async
        assert mods.is_abstract
        assert not mods.is_final
        assert mods.has(ModifierKind.STATIC)
        assert mods.has("async")

    def test_modifier_set_immutability(self):
        mods = ModifierSet(modifiers=[ModifierKind.STATIC])
        new_mods = mods.with_modifier(ModifierKind.FINAL)
        assert not mods.is_final
        assert new_mods.is_final


class TestSourceLocationAndRange:
    def test_source_range_valid(self):
        start = SourceLocation(line=10, column=4, offset=150)
        end = SourceLocation(line=15, column=2, offset=230)
        sr = SourceRange(start=start, end=end, byte_length=80)
        assert sr.start.line == 10
        assert sr.end.line == 15

    def test_source_range_invalid_end_before_start(self):
        start = SourceLocation(line=20, column=0)
        end = SourceLocation(line=10, column=0)
        with pytest.raises(SymbolValidationError):
            SourceRange(start=start, end=end)


class TestSymbolModel:
    def create_sample_symbol(self) -> Symbol:
        fqn = QualifiedName.from_string("com.company.AuthService.login")
        sym_id = generate_symbol_id("repo-xyz", Language.JAVA, fqn, SymbolKind.METHOD)
        
        src_info = SourceInformation(
            file_id="file-001",
            file_path="src/main/java/com/company/AuthService.java",
            range=SourceRange(
                start=SourceLocation(line=42, column=4, offset=1024),
                end=SourceLocation(line=58, column=5, offset=1450),
                byte_length=426
            ),
            parser_node_ref={"node_type": "method_declaration"}
        )
        
        doc = Documentation(
            summary="Authenticate user credentials",
            detailed_description="Validates password hash and returns JWT token.",
            doc_format=DocumentationFormat.JAVADOC,
            params={"username": "User login name", "password": "Raw password string"},
            returns="AuthResult object"
        )
        
        type_ref = TypeReference(
            name="AuthResult",
            raw_type="com.company.AuthResult",
            qualified_name=QualifiedName.from_string("com.company.AuthResult")
        )
        
        return Symbol(
            id=sym_id,
            fqn=fqn,
            name="login",
            kind=SymbolKind.METHOD,
            language=Language.JAVA,
            visibility=Visibility.public(),
            accessibility=Accessibility.read_write(),
            modifiers=ModifierSet(modifiers=[ModifierKind.STATIC, ModifierKind.SYNCHRONIZED]),
            source_info=src_info,
            doc=doc,
            type_ref=type_ref,
            annotations=[Annotation(name="Override"), Annotation(name="Transactional")],
            metadata=Metadata(tags=["auth", "security"], user_metadata={"owner_team": "security"})
        )

    def test_symbol_creation_and_fields(self):
        sym = self.create_sample_symbol()
        assert sym.name == "login"
        assert sym.kind == SymbolKind.METHOD
        assert sym.language == Language.JAVA
        assert sym.visibility.is_public
        assert sym.modifiers.is_static
        assert len(sym.annotations) == 2
        assert sym.metadata.tags == ["auth", "security"]

    def test_symbol_immutability(self):
        sym = self.create_sample_symbol()
        with pytest.raises((ValidationError, TypeError)):
            sym.name = "new_login"  # type: ignore

    def test_metadata_does_not_change_symbol_id(self):
        fqn = QualifiedName.from_string("app.service.get_data")
        id1 = generate_symbol_id("repo-1", Language.PYTHON, fqn, SymbolKind.FUNCTION)
        
        src_info = SourceInformation(
            file_id="f1",
            file_path="app/service.py",
            range=SourceRange(
                start=SourceLocation(line=1, column=0),
                end=SourceLocation(line=5, column=0)
            )
        )
        
        sym1 = Symbol(
            id=id1,
            fqn=fqn,
            name="get_data",
            kind=SymbolKind.FUNCTION,
            language=Language.PYTHON,
            source_info=src_info,
            metadata=Metadata(tags=["v1"])
        )
        
        sym2 = Symbol(
            id=id1,
            fqn=fqn,
            name="get_data",
            kind=SymbolKind.FUNCTION,
            language=Language.PYTHON,
            source_info=src_info,
            metadata=Metadata(tags=["v2", "ai_annotated"], ai_metadata={"confidence": 0.99})
        )
        
        assert sym1.id == sym2.id


class TestSerialization:
    def test_full_json_roundtrip(self):
        sym = TestSymbolModel().create_sample_symbol()
        json_str = symbol_to_json(sym, indent=True)
        assert "_schema_version" in json_str
        
        reconstructed = json_to_symbol(json_str)
        assert are_symbols_equal(sym, reconstructed)
        assert reconstructed.id == sym.id
        assert reconstructed.fqn == sym.fqn

    def test_dict_roundtrip(self):
        sym = TestSymbolModel().create_sample_symbol()
        d = symbol_to_dict(sym)
        assert d["_schema_version"] == "3.1.0"
        
        reconstructed = dict_to_symbol(d)
        assert reconstructed == sym

    def test_hash_symbol(self):
        sym = TestSymbolModel().create_sample_symbol()
        h1 = hash_symbol(sym)
        h2 = hash_symbol(sym)
        assert h1 == h2
        assert len(h1) == 64


class TestRelationships:
    def test_symbol_relationship_metadata_container(self):
        src_id = generate_symbol_id("repo-1", Language.TYPESCRIPT, "src.index.main", SymbolKind.FUNCTION)
        target_id = generate_symbol_id("repo-1", Language.TYPESCRIPT, "src.utils.log", SymbolKind.FUNCTION)
        
        rel = SymbolRelationship(
            relationship_kind=RelationshipKind.CALLS,
            source_symbol_id=src_id,
            target_symbol_id=target_id,
            target_fqn=QualifiedName.from_string("src.utils.log"),
            metadata={"async_call": True}
        )
        
        assert rel.relationship_kind == RelationshipKind.CALLS
        assert rel.source_symbol_id == src_id
        assert rel.target_symbol_id == target_id
        assert rel.metadata["async_call"] is True
