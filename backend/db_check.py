import asyncio
import uuid
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

# Database connection
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/devbrain"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_edges():
    with SessionLocal() as db:
        # Check edges
        edges_count = db.execute(text("SELECT COUNT(*) FROM edges")).scalar()
        print(f"Total edges: {edges_count}")
        
        edges_by_type = db.execute(text("SELECT edge_type, COUNT(*) FROM edges GROUP BY edge_type")).fetchall()
        print("\nEdges by type:")
        for etype, count in edges_by_type:
            print(f"  {etype}: {count}")
            
        nodes_count = db.execute(text("SELECT COUNT(*) FROM nodes")).scalar()
        print(f"\nTotal nodes: {nodes_count}")
        
        nodes_by_type = db.execute(text("SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type")).fetchall()
        print("\nNodes by type:")
        for ntype, count in nodes_by_type:
            print(f"  {ntype}: {count}")

if __name__ == "__main__":
    check_edges()
