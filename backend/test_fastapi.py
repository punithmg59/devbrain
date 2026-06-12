import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.main import app
from app.utils.auth import get_current_user
from app.models.user import User
from app.database import async_session_factory
from sqlalchemy import text
import sys

def run():
    repo_id = "5118615f-bcf5-48c8-aebc-47d59b5999b2"
    
    async def get_owner():
        async with async_session_factory() as db:
            res = await db.execute(text("SELECT user_id FROM repos WHERE id = :id"), {"id": repo_id})
            return res.scalar()
            
    owner_id = asyncio.run(get_owner())
    if not owner_id:
        print("Repo owner not found")
        sys.exit(1)
        
    async def mock_get_current_user():
        user = User()
        user.id = owner_id
        return user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    client = TestClient(app)

    response = client.get(f"/api/repos/{repo_id}/project-brain")
    print("STATUS:", response.status_code)
    if response.status_code != 200:
        print("ERROR:", response.text[:500])
    else:
        print("SUCCESS:", str(response.json())[:200])

if __name__ == "__main__":
    run()
