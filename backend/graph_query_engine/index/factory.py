"""
IndexFactory for Manufacturing Validated Lookup, Relationship, and Semantic Indexes.
"""

from typing import Optional

from graph_query_engine.index.base import BaseIndex
from graph_query_engine.index.builder import IndexBuilder
from graph_query_engine.index.descriptor import IndexDescriptor
from graph_query_engine.view.graph_view import GraphView


class IndexFactory:
    """
    Factory constructing validated BaseIndex instances from GraphView.
    """

    @classmethod
    def create_index(
        cls,
        index_name: str,
        graph_view: GraphView,
        descriptor: Optional[IndexDescriptor] = None,
    ) -> BaseIndex:
        """
        Creates and validates an index instance by index_name for the given graph_view.
        """
        builder = IndexBuilder()
        desc = descriptor or IndexDescriptor(name=index_name)
        builder.set_descriptor(desc)

        name_upper = index_name.upper()

        # Step 3.4 Semantic Indexes
        if "TYPE_HIERARCHY" in name_upper or "THIER" in name_upper:
            return builder.build_type_hierarchy_index(graph_view)
        elif "INHERITANCE" in name_upper:
            return builder.build_inheritance_index(graph_view)
        elif "INTERFACE" in name_upper or "IFACE" in name_upper:
            return builder.build_interface_implementation_index(graph_view)
        elif "API_ROUTE" in name_upper or "ROUTE" in name_upper:
            return builder.build_api_route_index(graph_view)
        elif "SYMBOL_REFERENCE" in name_upper or "REFERENCE" in name_upper:
            return builder.build_symbol_reference_index(graph_view)
        elif "IMPORT" in name_upper:
            return builder.build_import_index(graph_view)
        elif "MODULE" in name_upper:
            return builder.build_module_index(graph_view)
        elif "LANGUAGE" in name_upper:
            return builder.build_language_index(graph_view)
        elif "ANNOTATION" in name_upper or "DECORATOR" in name_upper:
            return builder.build_annotation_index(graph_view)
        elif "ATTRIBUTE" in name_upper:
            return builder.build_attribute_index(graph_view)
        # Step 3.3 Relationship Indexes
        elif "REVERSE_CSR" in name_upper or "RCSR" in name_upper:
            return builder.build_reverse_csr_adjacency_index(graph_view)
        elif "CSR" in name_upper:
            return builder.build_csr_adjacency_index(graph_view)
        elif "OUTGOING" in name_upper:
            return builder.build_outgoing_relationship_index(graph_view)
        elif "INCOMING" in name_upper:
            return builder.build_incoming_relationship_index(graph_view)
        elif "NODE_RELATIONSHIP" in name_upper:
            return builder.build_node_relationship_index(graph_view)
        elif "RELATIONSHIP_TYPE" in name_upper or "RELTYPE" in name_upper:
            return builder.build_relationship_type_index(graph_view)
        elif "RELATIONSHIP" in name_upper:
            return builder.build_relationship_index(graph_view)
        elif "SELF_LOOP" in name_upper or "LOOP" in name_upper:
            return builder.build_self_loop_index(graph_view)
        # Step 3.2 Lookup Indexes
        elif "NODE" in name_upper:
            return builder.build_node_index(graph_view)
        elif "EDGE" in name_upper:
            return builder.build_edge_index(graph_view)
        elif "SYMBOL" in name_upper:
            return builder.build_symbol_index(graph_view)
        elif "FILE" in name_upper:
            return builder.build_file_index(graph_view)
        elif "PACKAGE" in name_upper:
            return builder.build_package_index(graph_view)
        elif "NAMESPACE" in name_upper:
            return builder.build_namespace_index(graph_view)
        elif "QUALIFIED" in name_upper or "QNAME" in name_upper:
            return builder.build_qualified_name_index(graph_view)
        else:
            return builder.build_from_view(graph_view)


__all__ = ["IndexFactory"]
