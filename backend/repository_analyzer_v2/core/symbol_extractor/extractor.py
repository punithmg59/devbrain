"""
core/symbol_extractor/extractor.py
-----------------------------------
Symbol Extractor Facade and RawSymbolCollection Container.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from core.namespaces.tree import NamespaceTree
from core.symbol_extractor.diagnostics import SymbolExtractionDiagnostics
from core.symbol_extractor.models import (
    RawSymbol,
    SymbolExtractionStatistics,
    TemporaryExtractionID,
)
from core.symbol_extractor.python_extractor import PythonSymbolExtractor
from core.symbol_extractor.registry import SymbolExtractorRegistry
from core.symbol_extractor.validator import SymbolExtractionValidator
from core.symbols import Language
from core.symbols.ids import NamespaceID
from models.parser import ParserResult

# Automatically register PythonSymbolExtractor
SymbolExtractorRegistry.register(Language.PYTHON, PythonSymbolExtractor())


class RawSymbolCollection(BaseModel):
    """
    Canonical, Immutable RawSymbolCollection output container.
    
    Serves as the frozen contract produced by Step 3.3 and consumed by Step 3.4.
    """
    repository_id: str = Field(..., description="Repository identifier")
    symbols: List[RawSymbol] = Field(default_factory=list, description="Extracted raw symbol declarations list")
    symbols_by_namespace: Dict[NamespaceID, List[TemporaryExtractionID]] = Field(
        default_factory=dict,
        description="NamespaceID to TemporaryExtractionIDs index"
    )
    symbols_by_file: Dict[str, List[TemporaryExtractionID]] = Field(
        default_factory=dict,
        description="File path to TemporaryExtractionIDs index"
    )
    statistics: SymbolExtractionStatistics = Field(
        default_factory=SymbolExtractionStatistics,
        description="Extraction statistics metrics"
    )
    diagnostics: SymbolExtractionDiagnostics = Field(
        default_factory=SymbolExtractionDiagnostics,
        description="Extraction diagnostics report"
    )

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }

    @field_validator("symbols_by_namespace", mode="before")
    @classmethod
    def _validate_namespace_map_keys(cls, v: Any) -> Any:
        if isinstance(v, dict):
            new_dict = {}
            for k, val in v.items():
                key_obj = NamespaceID(value=k) if isinstance(k, str) else k
                new_dict[key_obj] = val
            return new_dict
        return v

    def get_symbol(self, temp_id: TemporaryExtractionID) -> Optional[RawSymbol]:
        """Fetch a RawSymbol by its TemporaryExtractionID."""
        for sym in self.symbols:
            if sym.temp_id == temp_id:
                return sym
        return None

    def get_symbols_in_namespace(self, namespace_id: NamespaceID) -> List[RawSymbol]:
        """Fetch all RawSymbols declared inside a specific NamespaceID."""
        temp_ids = self.symbols_by_namespace.get(namespace_id, [])
        return [sym for sym in self.symbols if sym.temp_id in temp_ids]

    def get_symbols_in_file(self, file_path: str) -> List[RawSymbol]:
        """Fetch all RawSymbols declared within a specific file."""
        temp_ids = self.symbols_by_file.get(file_path, [])
        return [sym for sym in self.symbols if sym.temp_id in temp_ids]


class SymbolExtractor:
    """
    Facade engine converting ParserResults and NamespaceTree into a RawSymbolCollection.
    """

    def extract_symbols(
        self,
        parser_results: List[ParserResult],
        tree: NamespaceTree
    ) -> RawSymbolCollection:
        """
        Main Facade Entrypoint.
        """
        start_time = time.perf_counter()
        repository_id = tree.repository_id
        extracted_symbols: List[RawSymbol] = []
        diagnostics = SymbolExtractionDiagnostics()

        by_ns: Dict[NamespaceID, List[TemporaryExtractionID]] = {}
        by_file: Dict[str, List[TemporaryExtractionID]] = {}
        kind_counts: Dict[str, int] = {}
        lang_counts: Dict[str, int] = {}

        for pr in parser_results:
            try:
                lang = Language(pr.language.value.lower()) if hasattr(pr.language, "value") else Language.PYTHON
                extractor = SymbolExtractorRegistry.get_extractor(lang)
                
                file_symbols = extractor.extract(pr, tree, repository_id)
                for sym in file_symbols:
                    extracted_symbols.append(sym)
                    
                    by_ns.setdefault(sym.namespace_id, []).append(sym.temp_id)
                    by_file.setdefault(sym.file_path, []).append(sym.temp_id)

                    k_str = sym.kind.value
                    kind_counts[k_str] = kind_counts.get(k_str, 0) + 1
                    
                    l_str = sym.language.value
                    lang_counts[l_str] = lang_counts.get(l_str, 0) + 1

            except Exception as e:
                diagnostics = diagnostics.add_error(
                    message=f"Error extracting symbols from file '{pr.file_path}': {str(e)}",
                    file_path=pr.file_path,
                    code="ERR_SYMBOL_EXTRACTION_FAILED"
                )

        # Integrity Validation
        val_diags = SymbolExtractionValidator.validate(extracted_symbols, tree, repository_id)
        if val_diags.diagnostics:
            all_diags = diagnostics.diagnostics + val_diags.diagnostics
            diagnostics = SymbolExtractionDiagnostics(diagnostics=all_diags)

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        stats = SymbolExtractionStatistics(
            total_symbols=len(extracted_symbols),
            duration_ms=duration_ms,
            symbols_by_kind=kind_counts,
            symbols_by_language=lang_counts
        )

        return RawSymbolCollection(
            repository_id=repository_id,
            symbols=extracted_symbols,
            symbols_by_namespace=by_ns,
            symbols_by_file=by_file,
            statistics=stats,
            diagnostics=diagnostics
        )
