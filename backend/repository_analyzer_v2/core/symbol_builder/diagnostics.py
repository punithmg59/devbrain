"""
core/symbol_builder/diagnostics.py
-----------------------------------
Aggregate Pipeline Diagnostics container for Step 3.6.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

from core.namespaces.diagnostics import NamespaceDiagnostics
from core.namespaces.enums import DiagnosticSeverity
from core.symbol_extractor.diagnostics import SymbolExtractionDiagnostics
from core.symbol_identity.diagnostics import IdentityDiagnostics
from core.symbol_table.diagnostics import SymbolTableDiagnostics


class PipelineDiagnosticRecord(BaseModel):
    """Single diagnostic record emitted during pipeline orchestration."""
    message: str = Field(..., description="Human-readable diagnostic description")
    stage_name: str = Field(..., description="Pipeline stage identifier name")
    severity: DiagnosticSeverity = Field(
        default=DiagnosticSeverity.WARNING,
        description="Diagnostic severity level"
    )
    file_path: Optional[str] = Field(default=None, description="Associated file path if applicable")
    line: Optional[int] = Field(default=None, description="1-indexed line number")
    column: Optional[int] = Field(default=None, description="0-indexed column offset")
    code: Optional[str] = Field(default=None, description="Diagnostic error code identifier")

    model_config = {
        "frozen": True
    }


class PipelineDiagnostics(BaseModel):
    """
    Aggregated Pipeline Diagnostics container combining diagnostics from all 4 builder stages.
    """
    namespace_diagnostics: NamespaceDiagnostics = Field(
        default_factory=NamespaceDiagnostics,
        description="Diagnostics from Step 3.2 Namespace Builder"
    )
    extraction_diagnostics: SymbolExtractionDiagnostics = Field(
        default_factory=SymbolExtractionDiagnostics,
        description="Diagnostics from Step 3.3 Symbol Extractor"
    )
    identity_diagnostics: IdentityDiagnostics = Field(
        default_factory=IdentityDiagnostics,
        description="Diagnostics from Step 3.4 Symbol Identity Builder"
    )
    symbol_table_diagnostics: SymbolTableDiagnostics = Field(
        default_factory=SymbolTableDiagnostics,
        description="Diagnostics from Step 3.5 Symbol Table Builder"
    )
    pipeline_records: List[PipelineDiagnosticRecord] = Field(
        default_factory=list,
        description="Orchestrator-level diagnostic records"
    )

    model_config = {
        "frozen": True
    }

    @property
    def has_errors(self) -> bool:
        return (
            self.namespace_diagnostics.has_errors
            or self.extraction_diagnostics.has_errors
            or self.identity_diagnostics.has_errors
            or self.symbol_table_diagnostics.has_errors
            or any(r.severity == DiagnosticSeverity.ERROR for r in self.pipeline_records)
        )

    def add_pipeline_error(self, message: str, stage_name: str, file_path: Optional[str] = None, code: Optional[str] = None) -> PipelineDiagnostics:
        rec = PipelineDiagnosticRecord(
            message=message,
            stage_name=stage_name,
            severity=DiagnosticSeverity.ERROR,
            file_path=file_path,
            code=code
        )
        return PipelineDiagnostics(
            namespace_diagnostics=self.namespace_diagnostics,
            extraction_diagnostics=self.extraction_diagnostics,
            identity_diagnostics=self.identity_diagnostics,
            symbol_table_diagnostics=self.symbol_table_diagnostics,
            pipeline_records=self.pipeline_records + [rec]
        )
