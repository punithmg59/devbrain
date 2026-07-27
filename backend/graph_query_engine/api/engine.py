"""
Public Query API Engine Facade.

Official primary entrypoint into the DevBrain Graph Query Engine.
Translates high-level engineering questions into pipeline execution requests.
Internal planner, traversal, and graph algorithms remain strictly hidden.
"""

from typing import Any, Dict, List, Optional, Union

from graph_query_engine.api.builder import ApiQueryBuilder
from graph_query_engine.api.context import QueryContext
from graph_query_engine.api.exceptions import SessionNotFoundException
from graph_query_engine.api.executor import QueryExecutor
from graph_query_engine.api.options import QueryOptions
from graph_query_engine.api.request import QueryRequest
from graph_query_engine.api.response import QueryResponse
from graph_query_engine.api.session import QuerySession
from graph_query_engine.contracts.api import IQueryEngineAPI


class QueryEngine(IQueryEngineAPI):
    """
    Official Public Query API Facade for DevBrain Graph Query Engine.
    Exposes high-level engineering-centric methods.
    """

    def __init__(
        self,
        executor: Optional[QueryExecutor] = None,
        graph_view: Optional[Any] = None,
        index_layer: Optional[Any] = None,
    ) -> None:
        self.executor = executor or QueryExecutor()
        self.graph_view = graph_view
        self.index_layer = index_layer
        self.sessions: Dict[str, QuerySession] = {}

    def set_graph_view(self, graph_view: Any, index_layer: Optional[Any] = None) -> None:
        """Sets active GraphView and IndexLayer for execution."""
        self.graph_view = graph_view
        self.index_layer = index_layer

    # --- Standard Protocol Implementation ---
    def query(self, query_str: str, **params: Any) -> QueryResponse:
        """Executes a query string against the engine."""
        return self.execute_query(query_str, parameters=params)

    # --- Session Management ---
    def create_session(self, default_context: Optional[QueryContext] = None) -> QuerySession:
        """Creates a new QuerySession."""
        session = QuerySession(default_context=default_context, executor=self.executor)
        self.sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> QuerySession:
        """Retrieves an existing QuerySession by ID."""
        if session_id not in self.sessions:
            raise SessionNotFoundException(session_id)
        return self.sessions[session_id]

    # --- Dispatcher Helper ---
    def _dispatch(
        self,
        operation: str,
        target: str = "",
        context: Optional[QueryContext] = None,
        options: Optional[QueryOptions] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> QueryResponse:
        req = (
            ApiQueryBuilder(operation=operation, target=target)
            .context(context or QueryContext())
            .options(options or QueryOptions())
        )
        if parameters:
            for k, v in parameters.items():
                req = req.parameter(k, v)
        return self.executor.execute(req.build(), graph_view=self.graph_view, index_layer=self.index_layer)

    # --- Node & Entity Lookups ---
    def lookup_node(self, node_id: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Looks up a node by its ID."""
        return self._dispatch("lookup_node", target=node_id, context=context, options=options)

    def lookup_nodes(self, node_ids: List[str], context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Looks up multiple nodes by IDs."""
        return self._dispatch("lookup_nodes", target=",".join(node_ids), context=context, options=options, parameters={"node_ids": node_ids})

    def lookup_file(self, path: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Looks up a file node by path."""
        return self._dispatch("lookup_file", target=path, context=context, options=options)

    def lookup_folder(self, path: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Looks up a folder node by path."""
        return self._dispatch("lookup_folder", target=path, context=context, options=options)

    def lookup_class(self, class_name: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Looks up a class symbol by name."""
        return self._dispatch("lookup_class", target=class_name, context=context, options=options)

    def lookup_function(self, func_name: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Looks up a function symbol by name."""
        return self._dispatch("lookup_function", target=func_name, context=context, options=options)

    def lookup_method(self, method_name: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Looks up a method symbol by name."""
        return self._dispatch("lookup_method", target=method_name, context=context, options=options)

    def lookup_interface(self, interface_name: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Looks up an interface symbol by name."""
        return self._dispatch("lookup_interface", target=interface_name, context=context, options=options)

    def lookup_service(self, service_name: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Looks up a service component by name."""
        return self._dispatch("lookup_service", target=service_name, context=context, options=options)

    def lookup_api(self, api_name: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Looks up an API definition by name."""
        return self._dispatch("lookup_api", target=api_name, context=context, options=options)

    def lookup_route(self, route_pattern: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Looks up an API route pattern."""
        return self._dispatch("lookup_route", target=route_pattern, context=context, options=options)

    def lookup_symbol(self, symbol: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Looks up a general symbol by name or ID."""
        return self._dispatch("lookup_symbol", target=symbol, context=context, options=options)

    # --- Engineering Graph Navigation & Relationships ---
    def find_callers(self, target_symbol: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Finds callers invoking the target symbol."""
        return self._dispatch("find_callers", target=target_symbol, context=context, options=options)

    def find_callees(self, target_symbol: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Finds callees invoked by the target symbol."""
        return self._dispatch("find_callees", target=target_symbol, context=context, options=options)

    def find_dependencies(self, target_symbol: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Finds outgoing dependencies of target symbol."""
        return self._dispatch("find_dependencies", target=target_symbol, context=context, options=options)

    def find_dependents(self, target_symbol: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Finds incoming dependents depending on target symbol."""
        return self._dispatch("find_dependents", target=target_symbol, context=context, options=options)

    def find_imports(self, target_symbol: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Finds module imports for target symbol."""
        return self._dispatch("find_imports", target=target_symbol, context=context, options=options)

    def find_exports(self, target_symbol: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Finds module exports for target symbol."""
        return self._dispatch("find_exports", target=target_symbol, context=context, options=options)

    def find_neighbors(self, node_id: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Finds direct graph neighbors of node_id."""
        return self._dispatch("find_neighbors", target=node_id, context=context, options=options)

    def find_related_nodes(self, node_id: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Finds semantically related nodes."""
        return self._dispatch("find_related_nodes", target=node_id, context=context, options=options)

    def find_reachable_nodes(self, start_node: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Finds all nodes reachable from start_node."""
        return self._dispatch("find_reachable_nodes", target=start_node, context=context, options=options)

    def find_paths(self, source_node: str, target_node: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Finds paths connecting source_node and target_node."""
        return self._dispatch("find_paths", target=source_node, context=context, options=options, parameters={"destination": target_node})

    def find_shortest_path(self, source_node: str, target_node: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Finds the shortest path connecting source_node and target_node."""
        return self._dispatch("find_shortest_path", target=source_node, context=context, options=options, parameters={"destination": target_node})

    def find_cycles(self, start_node: str = "", context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Finds dependency cycles starting from start_node."""
        return self._dispatch("find_cycles", target=start_node, context=context, options=options)

    def find_connected_components(self, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Finds connected components in the graph."""
        return self._dispatch("find_connected_components", context=context, options=options)

    # --- Search & Repository Discovery ---
    def query_repository(self, query_str: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Queries repository using query string."""
        return self._dispatch("query_repository", target=query_str, context=context, options=options)

    def search_repository(self, pattern: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Searches repository for pattern match."""
        return self._dispatch("search_repository", target=pattern, context=context, options=options)

    def search_symbols(self, pattern: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Searches symbols matching pattern."""
        return self._dispatch("search_symbols", target=pattern, context=context, options=options)

    def search_by_name(self, name_pattern: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Searches entities by name pattern."""
        return self._dispatch("search_by_name", target=name_pattern, context=context, options=options)

    def search_by_type(self, entity_type: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Searches entities by entity type."""
        return self._dispatch("search_by_type", target=entity_type, context=context, options=options)

    def search_by_metadata(self, metadata_key: str, metadata_value: Any, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Searches entities by metadata key/value."""
        return self._dispatch("search_by_metadata", target=metadata_key, context=context, options=options, parameters={"value": metadata_value})

    def search_by_annotation(self, annotation_name: str, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Searches entities by decorator or annotation name."""
        return self._dispatch("search_by_annotation", target=annotation_name, context=context, options=options)

    # --- Generic Execution Methods ---
    def execute_query(self, query: Union[str, QueryRequest], context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None, parameters: Optional[Dict[str, Any]] = None) -> QueryResponse:
        """Executes a query string or QueryRequest."""
        if isinstance(query, QueryRequest):
            return self.executor.execute(query, graph_view=self.graph_view, index_layer=self.index_layer)
        return self._dispatch("execute_query", target=query, context=context, options=options, parameters=parameters)

    def execute_execution_plan(self, execution_plan: Any, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Executes an existing ExecutionPlan."""
        req = QueryRequest(
            operation="execute_execution_plan",
            target=getattr(execution_plan, "execution_plan_id", "plan"),
            context=context or QueryContext(),
            options=options or QueryOptions(),
        )
        return self.executor.execute(req, graph_view=self.graph_view, index_layer=self.index_layer)

    def execute_traversal(self, traversal_request: Any, context: Optional[QueryContext] = None, options: Optional[QueryOptions] = None) -> QueryResponse:
        """Executes a low-level traversal request."""
        req = QueryRequest(
            operation="execute_traversal",
            target=str(traversal_request),
            context=context or QueryContext(),
            options=options or QueryOptions(),
        )
        return self.executor.execute(req, graph_view=self.graph_view, index_layer=self.index_layer)


__all__ = ["QueryEngine"]
