"""
tests/test_reference_index.py
------------------------------
Unit tests for ReferenceIndex multi-index lookups.
"""

from models.reference_models import (
    ReferenceKind,
    ReferenceRecord,
    ReferenceResolution,
)
from analysis.reference_resolution.reference_index import ReferenceIndex


class TestReferenceIndex:
    def test_multi_index_lookups(self):
        index = ReferenceIndex()

        rec = ReferenceRecord(
            id="ref-1",
            file_path="app/auth.py",
            symbol_id="sym-auth-service",
            symbol_name="AuthService",
            kind=ReferenceKind.CLASS_DEFINITION,
            scope_id="s-mod",
            line=5,
            column=0,
            end_line=5,
            end_column=18,
            is_definition=True,
        )
        res = ReferenceResolution(
            reference_id="ref-1",
            symbol_id="sym-auth-service",
            symbol_fqn="app.auth.AuthService",
            scope_id="s-mod",
            is_resolved=True,
        )

        index.add_reference(rec, res)

        assert len(index) == 1
        assert index.find_references("sym-auth-service") == [rec]
        assert index.find_file_references("app/auth.py") == [rec]
        assert index.find_scope_references("s-mod") == [rec]
        assert index.find_references_by_kind(ReferenceKind.CLASS_DEFINITION) == [rec]
