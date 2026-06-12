import asyncio
import json
from sqlalchemy import text
from app.database import async_session_factory
from app.schemas.repo_detail import ImpactAnalysisRequest
from app.services.impact_analysis_v2 import run_impact_analysis

async def main():
    async with async_session_factory() as db:
        # Get first repo
        r = await db.execute(text("SELECT id, user_id FROM repos LIMIT 1"))
        row = r.first()
        if not row:
            print("No repos found")
            return
        repo_id, user_id = row
        print(f"Repo ID: {repo_id}")

        # Let's see if there is _batch_summarize
        n = await db.execute(text("SELECT id, name, node_type FROM nodes WHERE name='_batch_summarize' LIMIT 1"))
        node_row = n.first()
        if not node_row:
            # Get any function or method
            n = await db.execute(text("SELECT id, name, node_type FROM nodes LIMIT 1"))
            node_row = n.first()
            if not node_row:
                print("No nodes found")
                return

        node_id, name, node_type = node_row
        print(f"Target node for impact: '{name}' (Type: {node_type})")

        # Let's test delete scenario
        req = ImpactAnalysisRequest(query=name, scenario="delete")
        print("\n--- Running delete scenario impact analysis ---")
        res = await run_impact_analysis(req, repo_id, db)
        
        print(f"Resolved Node: {res.resolved_node_name} ({res.resolved_node_type}) in {res.resolved_file_path}")
        print(f"Fuzzy matches count: {len(res.fuzzy_matches)}")
        print(f"Blast Radius:")
        print(f"  Direct dependents: {res.blast_radius.direct_dependents}")
        print(f"  Indirect dependents: {res.blast_radius.indirect_dependents}")
        print(f"  API impact: {res.blast_radius.api_impact}")
        print(f"  DB impact: {res.blast_radius.database_impact}")
        print(f"  Service impact: {res.blast_radius.service_impact}")
        print(f"  File impact: {res.blast_radius.file_impact}")
        print(f"  Auth impact: {res.blast_radius.auth_impact}")
        print(f"  Class impact: {res.blast_radius.class_impact}")
        print(f"  Total nodes affected: {res.blast_radius.total_nodes_affected}")
        print(f"  Cycles detected: {res.blast_radius.cycles_detected}")
        
        print(f"Risk Score: {res.risk.score} ({res.risk.level})")
        print("Factors contributing:")
        for factor in res.risk.factors:
            print(f"  - {factor.factor}: {factor.count} (weight: {factor.weight}) -> contribution: {factor.contribution}")
            
        print("\nExecutive Summary:")
        print(res.executive_summary)
        
        print("\nBusiness Impact:")
        for bi in res.business_impact:
            print(f"  - {bi}")
            
        print("\nDeveloper Impact:")
        for di in res.developer_impact:
            print(f"  - {di}")
            
        print("\nRecommended Tests:")
        for rt in res.recommended_tests:
            print(f"  - {rt}")
            
        print(f"\nDeployment Recommendation:\n  {res.deployment_recommendation}")
        print(f"Rollback Strategy:\n  {res.rollback_strategy}")
        
        print(f"\nAnalysis Time: {res.analysis_time_ms} ms")

if __name__ == '__main__':
    asyncio.run(main())
