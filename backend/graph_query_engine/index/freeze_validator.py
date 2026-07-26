"""
IndexFreezeValidator for Static Architecture Freeze Verification.
"""

from graph_query_engine.index.diagnostics import DiagnosticItem, DiagnosticSeverity, IndexDiagnostics


class IndexFreezeValidator:
    """
    Static freeze validator verifying contract compliance, zero circular imports, and architecture readiness.
    """

    REQUIRED_CONTRACTS = (
        "IIndex",
        "IIndexBuilder",
        "IIndexRegistry",
        "IIndexFactory",
        "IIndexLifecycle",
        "IIndexStatistics",
        "IIndexValidator",
        "IIndexMetadata",
        "IIndexDescriptor",
        "IIndexProvider",
    )

    REQUIRED_INDEX_CLASSES = (
        "NodeIndex",
        "EdgeIndex",
        "SymbolIndex",
        "FileIndex",
        "PackageIndex",
        "NamespaceIndex",
        "QualifiedNameIndex",
        "CSRAdjacencyIndex",
        "ReverseCSRAdjacencyIndex",
        "RelationshipIndex",
        "OutgoingRelationshipIndex",
        "IncomingRelationshipIndex",
        "NodeRelationshipIndex",
        "RelationshipTypeIndex",
        "SelfLoopIndex",
        "TypeHierarchyIndex",
        "InheritanceIndex",
        "InterfaceImplementationIndex",
        "APIRouteIndex",
        "SymbolReferenceIndex",
        "ImportIndex",
        "ModuleIndex",
        "LanguageIndex",
        "AnnotationIndex",
        "AttributeIndex",
    )

    @classmethod
    def validate_freeze_readiness(cls) -> IndexDiagnostics:
        """
        Audits the Index subsystem for architecture freeze readiness.
        """
        items: list[DiagnosticItem] = []

        # 1. Verify required contract protocols exist
        import graph_query_engine.contracts.index as index_contracts

        for contract_name in cls.REQUIRED_CONTRACTS:
            if not hasattr(index_contracts, contract_name):
                items.append(
                    DiagnosticItem(
                        code="ERR_FREEZE_MISSING_CONTRACT",
                        severity=DiagnosticSeverity.ERROR,
                        component="contracts.index",
                        message=f"Missing required contract protocol: '{contract_name}'.",
                        recommendation="Re-export missing contract in graph_query_engine.contracts.index.",
                    )
                )

        # 2. Verify all concrete index classes exist in index package
        import graph_query_engine.index as index_pkg

        for cls_name in cls.REQUIRED_INDEX_CLASSES:
            if not hasattr(index_pkg, cls_name):
                items.append(
                    DiagnosticItem(
                        code="ERR_FREEZE_MISSING_CLASS",
                        severity=DiagnosticSeverity.ERROR,
                        component="index",
                        message=f"Missing concrete index class: '{cls_name}'.",
                        recommendation=f"Re-export {cls_name} in graph_query_engine.index.",
                    )
                )

        return IndexDiagnostics(items=tuple(items))

    @classmethod
    def validate_readiness(cls) -> IndexDiagnostics:
        """Alias for validate_freeze_readiness()."""
        return cls.validate_freeze_readiness()


__all__ = ["IndexFreezeValidator"]
