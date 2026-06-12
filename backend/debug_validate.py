"""Test: Can NodeResponse.model_validate work with a Node ORM object?"""
import asyncio
import sys
sys.path.insert(0, ".")

async def main():
    from app.database import engine, async_session_factory
    from app.models import Node
    from app.schemas.repo_detail import NodeResponse
    from sqlalchemy import select

    async with async_session_factory() as session:
        result = await session.execute(select(Node).limit(1))
        node = result.scalar_one_or_none()
        if not node:
            print("No nodes found!")
            return

        print(f"Got node: {node}")
        print(f"Node attributes: {[a for a in dir(node) if not a.startswith('_')]}")
        
        # Check if the problematic attributes exist
        for attr in ['dependencies', 'responsibilities', 'inputs', 'outputs', 'related_components', 'call_flow']:
            exists = hasattr(node, attr)
            print(f"  hasattr(node, '{attr}') = {exists}")

        # Try model_validate
        try:
            resp = NodeResponse.model_validate(node)
            print(f"\nmodel_validate SUCCEEDED!")
            print(f"  node_type={resp.node_type}, name={resp.name}")
        except Exception as e:
            print(f"\nmodel_validate FAILED: {type(e).__name__}: {e}")

asyncio.run(main())
