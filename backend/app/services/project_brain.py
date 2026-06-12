import uuid
from typing import List, Dict, Any

from sqlalchemy import select, func, text, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB

from app.models.node import Node
from app.models.edge import Edge
from app.schemas.repo_detail import (
    ProjectBrainResponse,
    RepoIntelligenceScore,
    ArchitectureMap,
    DependencyHealth,
    CriticalFunction,
    ConnectedComponent,
    DatabaseHotspot,
    HighRiskApi,
    ArchitectureViolation
)

async def get_project_brain_dashboard(db: AsyncSession, repo_id: str) -> ProjectBrainResponse:
    repo_uuid = uuid.UUID(repo_id)

    # 1. Architecture Map
    frontend_components = await db.scalar(
        select(func.count(Node.id)).where(Node.repo_id == repo_uuid, Node.node_type.in_(["component", "page"]))
    ) or 0
    
    backend_services = await db.scalar(
        select(func.count(Node.id)).where(Node.repo_id == repo_uuid, Node.node_type == "class", Node.name.ilike("%Service%"))
    ) or 0

    api_routes = await db.scalar(
        select(func.count(Node.id)).where(Node.repo_id == repo_uuid, Node.node_type == "api_route")
    ) or 0

    database_tables = await db.scalar(
        select(func.count(Node.id)).where(Node.repo_id == repo_uuid, Node.node_type == "table")
    ) or 0

    architecture_map = ArchitectureMap(
        frontend_components=frontend_components,
        backend_services=backend_services,
        api_routes=api_routes,
        database_tables=database_tables
    )

    # 2. Dependency Health
    total_edges = await db.scalar(
        select(func.count(Edge.id)).where(Edge.repo_id == repo_uuid)
    ) or 0
    
    # We can approximate risky/circular/orphans
    risky_nodes_count = await db.scalar(
        select(func.count(Node.id)).where(Node.repo_id == repo_uuid, func.jsonb_array_length(func.cast(Node.potential_risks, JSONB)) > 0)
    ) or 0

    # Orphaned nodes (no incoming or outgoing edges)
    # Using subquery or not exists
    orphaned_res = await db.execute(
        text("""
        SELECT COUNT(id) FROM nodes 
        WHERE repo_id = :repo_id 
        AND id NOT IN (SELECT from_node_id FROM edges WHERE repo_id = :repo_id)
        AND id NOT IN (SELECT to_node_id FROM edges WHERE repo_id = :repo_id)
        """)
    , {"repo_id": repo_uuid})
    orphaned = orphaned_res.scalar() or 0

    dependency_health = DependencyHealth(
        healthy=max(0, total_edges - risky_nodes_count * 2), # Approximation
        risky=risky_nodes_count,
        circular=0, # Circular dependencies would require a recursive query, setting to 0 for now
        orphaned=orphaned
    )

    # 3. Critical Functions
    # Calculate based on inbound calls + api_usage
    critical_functions_raw = await db.execute(
        text("""
        SELECT n.id, n.name, n.full_path, 
               array_length(n.called_by, 1) as inbound_calls,
               (SELECT COUNT(*) FROM edges e WHERE e.to_node_id = n.id AND e.edge_type = 'api_calls') as api_usage,
               (SELECT COUNT(*) FROM edges e WHERE e.from_node_id = n.id AND e.edge_type IN ('reads_table', 'writes_table', 'updates_table', 'deletes_table')) as db_usage,
               (SELECT COUNT(*) FROM edges e WHERE e.from_node_id = n.id AND e.edge_type = 'uses_service') as service_usage
        FROM nodes n
        WHERE n.repo_id = :repo_id AND n.node_type IN ('function', 'method')
        ORDER BY array_length(n.called_by, 1) DESC NULLS LAST
        LIMIT 20
        """),
        {"repo_id": repo_uuid}
    )

    critical_functions = []
    for row in critical_functions_raw:
        inbound = row.inbound_calls or 0
        api_usg = row.api_usage or 0
        db_usg = row.db_usage or 0
        srv_usg = row.service_usage or 0
        importance = inbound * 5 + api_usg * 10 + db_usg * 8 + srv_usg * 3
        
        critical_functions.append(CriticalFunction(
            node_id=str(row.id),
            name=row.name,
            file_path=row.full_path,
            importance_score=importance,
            inbound_calls=inbound,
            api_usage=api_usg,
            db_usage=db_usg,
            service_usage=srv_usg
        ))
    
    # Sort by actual importance score
    critical_functions.sort(key=lambda x: x.importance_score, reverse=True)

    # 4. Connected Components
    # Nodes with the most edges (in + out)
    connected_raw = await db.execute(
        text("""
        SELECT n.id, n.name, 
               (SELECT COUNT(*) FROM edges e WHERE e.from_node_id = n.id OR e.to_node_id = n.id) as degree
        FROM nodes n
        WHERE n.repo_id = :repo_id
        ORDER BY degree DESC
        LIMIT 10
        """),
        {"repo_id": repo_uuid}
    )
    
    connected_components = [
        ConnectedComponent(
            node_id=str(row.id),
            name=row.name,
            degree=row.degree or 0
        )
        for row in connected_raw
    ]

    # 5. Database Hotspots
    db_hotspots_raw = await db.execute(
        text("""
        SELECT * FROM (
            SELECT n.id, n.name,
                   (SELECT COUNT(*) FROM edges e WHERE e.to_node_id = n.id AND e.edge_type = 'reads_table') as reads,
                   (SELECT COUNT(*) FROM edges e WHERE e.to_node_id = n.id AND e.edge_type = 'writes_table') as writes,
                   (SELECT COUNT(*) FROM edges e WHERE e.to_node_id = n.id AND e.edge_type = 'updates_table') as updates,
                   (SELECT COUNT(*) FROM edges e WHERE e.to_node_id = n.id AND e.edge_type = 'deletes_table') as deletes
            FROM nodes n
            WHERE n.repo_id = :repo_id AND n.node_type = 'table'
        ) sub
        ORDER BY (reads + writes + updates + deletes) DESC
        LIMIT 10
        """),
        {"repo_id": repo_uuid}
    )

    database_hotspots = []
    for row in db_hotspots_raw:
        # Fetch touching functions for drill down
        touching_raw = await db.execute(
            text("""
            SELECT n.name
            FROM nodes n
            JOIN edges e ON e.from_node_id = n.id
            WHERE e.to_node_id = :target_id 
              AND e.edge_type IN ('reads_table', 'writes_table', 'updates_table', 'deletes_table')
            LIMIT 50
            """),
            {"target_id": row.id}
        )
        touching_funcs = [tr.name for tr in touching_raw]
        
        database_hotspots.append(DatabaseHotspot(
            node_id=str(row.id),
            name=row.name,
            total_reads=row.reads or 0,
            total_writes=row.writes or 0,
            total_updates=row.updates or 0,
            total_deletes=row.deletes or 0,
            touching_functions=touching_funcs
        ))

    # 6. High Risk APIs
    high_risk_apis_raw = await db.execute(
        text("""
        SELECT * FROM (
            SELECT n.id, n.name, n.route_path, n.calls,
                   (SELECT COUNT(*) FROM edges e WHERE e.from_node_id = n.id AND e.edge_type LIKE '%_table') as tables_touched,
                   array_length(n.calls, 1) as functions_touched
            FROM nodes n
            WHERE n.repo_id = :repo_id AND n.node_type = 'api_route'
        ) sub
        ORDER BY (tables_touched + COALESCE(functions_touched, 0)) DESC
        LIMIT 10
        """),
        {"repo_id": repo_uuid}
    )

    high_risk_apis = []
    for row in high_risk_apis_raw:
        tbl_t = row.tables_touched or 0
        fn_t = row.functions_touched or 0
        risk_score = tbl_t * 10 + fn_t * 2
        
        high_risk_apis.append(HighRiskApi(
            node_id=str(row.id),
            name=row.name,
            route_path=row.route_path,
            risk_score=risk_score,
            tables_touched=tbl_t,
            functions_touched=fn_t
        ))
        
    high_risk_apis.sort(key=lambda x: x.risk_score, reverse=True)

    # 7. Architecture Violations
    architecture_violations = []
    
    # Violation: Direct DB Call from Controller/API
    direct_db_calls = await db.execute(
        text("""
        SELECT e.id, from_n.id as source_id, from_n.name as source_name, from_n.full_path, 
               to_n.id as target_id, to_n.name as target_name
        FROM edges e
        JOIN nodes from_n ON e.from_node_id = from_n.id
        JOIN nodes to_n ON e.to_node_id = to_n.id
        WHERE e.repo_id = :repo_id 
          AND from_n.node_type = 'api_route' 
          AND to_n.node_type = 'table'
        LIMIT 10
        """),
        {"repo_id": repo_uuid}
    )
    for row in direct_db_calls:
        architecture_violations.append(ArchitectureViolation(
            id=str(row.id),
            severity="High",
            rule_name="Direct Database Access",
            description=f"API route '{row.source_name}' directly accesses table '{row.target_name}'. Consider using a service layer.",
            source_node_id=str(row.source_id),
            target_node_id=str(row.target_id),
            file_path=row.full_path
        ))

    # Calculate overall Intelligence Score
    # Dummy calculation for now
    code_health = 85
    dependency_health_score = 90 if dependency_health.orphaned < 10 else 70
    architecture_health = max(0, 100 - len(architecture_violations) * 5)
    engineering_quality = 80
    risk_exposure = max(0, 100 - len(high_risk_apis) * 2)
    
    total_score = int((code_health + dependency_health_score + architecture_health + engineering_quality + risk_exposure) / 5)

    intelligence_score = RepoIntelligenceScore(
        total_score=total_score,
        code_health=code_health,
        dependency_health=dependency_health_score,
        architecture_health=architecture_health,
        engineering_quality=engineering_quality,
        risk_exposure=risk_exposure
    )

    return ProjectBrainResponse(
        repo_id=repo_id,
        intelligence_score=intelligence_score,
        architecture_map=architecture_map,
        dependency_health=dependency_health,
        critical_functions=critical_functions,
        connected_components=connected_components,
        database_hotspots=database_hotspots,
        high_risk_apis=high_risk_apis,
        architecture_violations=architecture_violations
    )
