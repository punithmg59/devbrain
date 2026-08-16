"""Architecture data service.

Reads the EXISTING repository graph (nodes / edges / repo_files) and reshapes it
for the Architecture workspace. No new tables, no AI, no explanation generation —
just scoped, indexed queries over what analysis already produced.
"""

import logging
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import Edge, Node, RepoFile
from app.schemas.architecture import (
    ArchitectureComponents,
    ArchitectureDependencies,
    ArchitectureOverview,
    ArchNodeSummary,
    ComponentGroup,
    DependencyEdge,
    NodeDetails,
    RelatedNode,
)

logger = logging.getLogger(__name__)

# ── Graph vocabulary (matches analysis_collect.py) ────────────────────
FRONTEND_LANGUAGES = ("JavaScript", "TypeScript", "Vue")
FUNCTION_TYPES = ("function", "method")
FRONTEND_NODE_TYPES = ("function", "method", "class")

CALL_EDGES = ("calls", "api_calls")
SERVICE_EDGES = ("uses_service",)
TABLE_EDGES = ("reads_table", "writes_table", "updates_table", "deletes_table")
DEPENDENCY_EDGES = ("imports", "dependency_injection", "auth_dependency", "inherits")

# Bounds keep responses fast and payloads predictable.
COMPONENT_ITEM_LIMIT = 500
DEPENDENCY_EDGE_LIMIT = 1000


def _summary(node: Node, file_path: str | None, language: str | None) -> ArchNodeSummary:
    return ArchNodeSummary(
        id=str(node.id),
        name=node.name,
        node_type=node.node_type,
        full_path=node.full_path,
        file_path=file_path,
        language=language,
        http_method=node.http_method,
        route_path=node.route_path,
        is_exported=bool(node.is_exported),
        is_async=bool(node.is_async),
        start_line=node.start_line,
        end_line=node.end_line,
    )


def _related(node: Node, file_path: str | None, language: str | None, edge_type: str) -> RelatedNode:
    base = _summary(node, file_path, language)
    return RelatedNode(**base.model_dump(), edge_type=edge_type)


class ArchitectureService:
    # ── Overview: just counts ─────────────────────────────────────────
    # One round trip: group by node_type AND whether the node is a frontend
    # component (frontend node_type living in a JS/TS/Vue file).
    async def get_overview(self, repo_id: UUID, db: AsyncSession) -> ArchitectureOverview:
        is_frontend = case(
            (
                Node.node_type.in_(FRONTEND_NODE_TYPES)
                & RepoFile.language.in_(FRONTEND_LANGUAGES),
                1,
            ),
            else_=0,
        )
        rows = (
            await db.execute(
                select(Node.node_type, is_frontend.label("fe"), func.count())
                .outerjoin(RepoFile, Node.file_id == RepoFile.id)
                .where(Node.repo_id == repo_id)
                .group_by(Node.node_type, "fe")
            )
        ).all()

        counts: dict[str, int] = {}
        frontend = 0
        for node_type, fe, c in rows:
            counts[node_type] = counts.get(node_type, 0) + int(c)
            if fe:
                frontend += int(c)

        total_files = (
            await db.execute(
                select(func.count()).select_from(RepoFile).where(RepoFile.repo_id == repo_id)
            )
        ).scalar() or 0
        total_dependencies = (
            await db.execute(
                select(func.count()).select_from(Edge).where(Edge.repo_id == repo_id)
            )
        ).scalar() or 0

        return ArchitectureOverview(
            frontend_components=int(frontend),
            backend_services=counts.get("service", 0),
            api_routes=counts.get("api_route", 0),
            database_tables=counts.get("database_table", 0),
            classes=counts.get("class", 0),
            functions=counts.get("function", 0) + counts.get("method", 0),
            external_apis=counts.get("external_api", 0),
            total_files=int(total_files),
            total_dependencies=int(total_dependencies),
        )

    # ── Components: grouped lists for the sidebar / future diagram ─────
    # Single round trip: fetch every component-bearing node once, bucket in
    # Python. Counts are exact; item lists are capped at COMPONENT_ITEM_LIMIT.
    async def get_components(self, repo_id: UUID, db: AsyncSession) -> ArchitectureComponents:
        component_types = (
            *FUNCTION_TYPES,
            "class",
            "api_route",
            "service",
            "database_table",
            "external_api",
        )
        rows = (
            await db.execute(
                select(Node, RepoFile.file_path, RepoFile.language)
                .outerjoin(RepoFile, Node.file_id == RepoFile.id)
                .where(Node.repo_id == repo_id, Node.node_type.in_(component_types))
                .order_by(Node.name)
            )
        ).all()

        buckets: dict[str, list[ArchNodeSummary]] = {
            "components": [],
            "apis": [],
            "services": [],
            "tables": [],
            "classes": [],
            "functions": [],
            "external_apis": [],
        }
        for node, file_path, language in rows:
            summary = _summary(node, file_path, language)
            nt = node.node_type
            if nt in FUNCTION_TYPES:
                buckets["functions"].append(summary)
            if nt == "class":
                buckets["classes"].append(summary)
            if nt == "api_route":
                buckets["apis"].append(summary)
            if nt == "service":
                buckets["services"].append(summary)
            if nt == "database_table":
                buckets["tables"].append(summary)
            if nt == "external_api":
                buckets["external_apis"].append(summary)
            if nt in FRONTEND_NODE_TYPES and language in FRONTEND_LANGUAGES:
                buckets["components"].append(summary)

        labels = {
            "components": "Architecture Components",
            "apis": "APIs",
            "services": "Services",
            "tables": "Database Tables",
            "classes": "Classes",
            "functions": "Functions",
            "external_apis": "External APIs",
        }
        order = ["components", "apis", "services", "tables", "classes", "functions", "external_apis"]
        groups = [
            ComponentGroup(
                key=key,
                label=labels[key],
                count=len(buckets[key]),
                items=buckets[key][:COMPONENT_ITEM_LIMIT],
            )
            for key in order
        ]
        return ArchitectureComponents(repo_id=str(repo_id), groups=groups)

    # ── Node details: callers / callees / services / tables / deps ────
    async def get_node_details(
        self, repo_id: UUID, node_id: UUID, db: AsyncSession
    ) -> NodeDetails | None:
        row = (
            await db.execute(
                select(Node, RepoFile.file_path, RepoFile.language)
                .outerjoin(RepoFile, Node.file_id == RepoFile.id)
                .where(Node.id == node_id, Node.repo_id == repo_id)
            )
        ).first()
        if not row:
            return None
        node, file_path, language = row

        # Get source code (decrypt if encrypted)
        source_code = None
        if node.raw_code_encrypted:
            from app.security.encryption import get_encryption_service
            try:
                encryption_service = get_encryption_service()
                source_code = await encryption_service.decrypt(node.raw_code_encrypted)
            except Exception as e:
                logger.warning(f"Failed to decrypt source code for node {node.id}: {e}")
                source_code = node.raw_code  # Fallback to unencrypted if available
        elif node.raw_code:
            source_code = node.raw_code

        # Get parent class if this is a method (check full_path for class.method pattern)
        parent_class = None
        if node.node_type == "method" and "." in node.full_path:
            # Extract class name from full_path (e.g., "FaceDetector.__del__" -> "FaceDetector")
            class_name = node.full_path.split(".")[-2]
            # Try to find the parent class node
            parent_row = (
                await db.execute(
                    select(Node, RepoFile.file_path, RepoFile.language)
                    .outerjoin(RepoFile, Node.file_id == RepoFile.id)
                    .where(
                        Node.repo_id == repo_id,
                        Node.node_type == "class",
                        Node.name == class_name,
                        Node.file_id == node.file_id,  # Same file
                    )
                )
            ).first()
            if parent_row:
                parent_node, parent_fp, parent_lang = parent_row
                parent_class = _summary(parent_node, parent_fp, parent_lang)

        # Outgoing: node → others
        ToNode = aliased(Node)
        out_rows = (
            await db.execute(
                select(Edge.edge_type, ToNode, RepoFile.file_path, RepoFile.language)
                .join(ToNode, ToNode.id == Edge.to_node_id)
                .outerjoin(RepoFile, ToNode.file_id == RepoFile.id)
                .where(Edge.repo_id == repo_id, Edge.from_node_id == node_id)
            )
        ).all()

        # Incoming: others → node
        FromNode = aliased(Node)
        in_rows = (
            await db.execute(
                select(Edge.edge_type, FromNode, RepoFile.file_path, RepoFile.language)
                .join(FromNode, FromNode.id == Edge.from_node_id)
                .outerjoin(RepoFile, FromNode.file_id == RepoFile.id)
                .where(Edge.repo_id == repo_id, Edge.to_node_id == node_id)
            )
        ).all()

        # Track all edge types found for evidence
        all_edge_types = set()
        for etype, _, _, _ in out_rows:
            all_edge_types.add(etype)
        for etype, _, _, _ in in_rows:
            all_edge_types.add(etype)

        callees: list[ArchNodeSummary] = []
        services: list[ArchNodeSummary] = []
        tables: list[RelatedNode] = []
        dependencies: list[RelatedNode] = []
        for etype, n, fp, lang in out_rows:
            if etype in CALL_EDGES:
                callees.append(_summary(n, fp, lang))
            elif etype in SERVICE_EDGES:
                services.append(_summary(n, fp, lang))
            elif etype in TABLE_EDGES:
                tables.append(_related(n, fp, lang, etype))
            elif etype in DEPENDENCY_EDGES:
                dependencies.append(_related(n, fp, lang, etype))

        callers: list[ArchNodeSummary] = [
            _summary(n, fp, lang) for etype, n, fp, lang in in_rows if etype in CALL_EDGES
        ]

        return NodeDetails(
            node=_summary(node, file_path, language),
            file_path=file_path,
            signature=node.signature,
            source_code=source_code,
            parent_class=parent_class,
            callers=callers,
            callees=callees,
            services=services,
            tables=tables,
            dependencies=dependencies,
            total_inbound_edges=len(in_rows),
            total_outbound_edges=len(out_rows),
            edge_types_found=list(all_edge_types),
        )

    # ── Repository-level dependency edges ─────────────────────────────
    async def get_dependencies(self, repo_id: UUID, db: AsyncSession) -> ArchitectureDependencies:
        count_rows = (
            await db.execute(
                select(Edge.edge_type, func.count())
                .where(Edge.repo_id == repo_id)
                .group_by(Edge.edge_type)
            )
        ).all()
        edge_type_counts = {etype: int(c) for etype, c in count_rows}
        total_edges = sum(edge_type_counts.values())

        FromNode = aliased(Node)
        ToNode = aliased(Node)
        edge_rows = (
            await db.execute(
                select(
                    Edge.from_node_id,
                    FromNode.name,
                    Edge.to_node_id,
                    ToNode.name,
                    Edge.edge_type,
                )
                .join(FromNode, FromNode.id == Edge.from_node_id)
                .join(ToNode, ToNode.id == Edge.to_node_id)
                .where(Edge.repo_id == repo_id)
                .limit(DEPENDENCY_EDGE_LIMIT)
            )
        ).all()

        edges = [
            DependencyEdge(
                from_node_id=str(fid),
                from_name=fname,
                to_node_id=str(tid),
                to_name=tname,
                edge_type=etype,
            )
            for fid, fname, tid, tname, etype in edge_rows
        ]
        return ArchitectureDependencies(
            repo_id=str(repo_id),
            total_edges=total_edges,
            edge_type_counts=edge_type_counts,
            edges=edges,
        )
