"""
scratch/test_fastapi_analysis.py
---------------------------------
Enterprise Real-World Benchmark Script analyzing a complete FastAPI repository using DependencyGraphFacade.
"""

import ast
import time
import sys
from pathlib import Path

# Add backend/repository_analyzer_v2 to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "repository_analyzer_v2"))

from core.facade import DependencyGraphFacade
from models.parser import ParserLanguage, ParserMetadata, ParserResult, ParserStatistics, ParserVersion


def convert_python_ast_node(node: ast.AST) -> list[dict]:
    """Recursively convert standard Python AST node into DevBrain AST dictionary format."""
    results = []

    if isinstance(node, ast.Module):
        children = []
        for stmt in node.body:
            children.extend(convert_python_ast_node(stmt))
        return [{
            "type": "module",
            "name": "module",
            "range": {"start": {"line": 1, "column": 0}, "end": {"line": 100, "column": 0}},
            "children": children
        }]

    elif isinstance(node, ast.ClassDef):
        superclasses = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                superclasses.append(base.id)
            elif isinstance(base, ast.Attribute):
                superclasses.append(base.attr)

        children = []
        for stmt in node.body:
            children.extend(convert_python_ast_node(stmt))

        start_line = getattr(node, "lineno", 1)
        end_line = getattr(node, "end_lineno", start_line + 5)

        results.append({
            "type": "class_def",
            "name": node.name,
            "superclasses": superclasses,
            "range": {"start": {"line": start_line, "column": node.col_offset}, "end": {"line": end_line, "column": 0}},
            "children": children
        })

    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        params = []
        for arg in node.args.args:
            p_name = arg.arg
            p_type = None
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    p_type = arg.annotation.id
                elif isinstance(arg.annotation, ast.Attribute):
                    p_type = arg.annotation.attr
            params.append({"name": p_name, "type": p_type})

        ret_type = None
        if node.returns:
            if isinstance(node.returns, ast.Name):
                ret_type = node.returns.id
            elif isinstance(node.returns, ast.Attribute):
                ret_type = node.returns.attr

        start_line = getattr(node, "lineno", 1)
        end_line = getattr(node, "end_lineno", start_line + 5)

        results.append({
            "type": "func_def",
            "name": node.name,
            "metadata": {"parameters": params, "return_type": ret_type},
            "range": {"start": {"line": start_line, "column": node.col_offset}, "end": {"line": end_line, "column": 0}},
            "children": []
        })

    elif isinstance(node, ast.Import):
        for alias in node.names:
            results.append({
                "type": "import_statement",
                "name": alias.name,
                "range": {"start": {"line": getattr(node, "lineno", 1), "column": node.col_offset}, "end": {"line": getattr(node, "lineno", 1), "column": 10}},
                "children": []
            })

    elif isinstance(node, ast.ImportFrom):
        mod = node.module or ""
        for alias in node.names:
            imported_name = f"{mod}.{alias.name}" if mod else alias.name
            results.append({
                "type": "import_from_statement",
                "name": imported_name,
                "range": {"start": {"line": getattr(node, "lineno", 1), "column": node.col_offset}, "end": {"line": getattr(node, "lineno", 1), "column": 10}},
                "children": []
            })

    return results


def parse_source_file(source_code: str, file_path: str) -> ParserResult:
    parsed_ast = ast.parse(source_code, filename=file_path)
    ast_roots = convert_python_ast_node(parsed_ast)
    ast_root = ast_roots[0] if ast_roots else {"type": "module", "name": "empty", "children": []}

    line_count = source_code.count("\n") + 1
    return ParserResult(
        job_id=f"job-{hash(file_path)}",
        file_path=file_path,
        language=ParserLanguage.PYTHON,
        statistics=ParserStatistics(lines_parsed=line_count, node_count=len(ast_roots)),
        metadata=ParserMetadata(
            parser_name="python-ast",
            language=ParserLanguage.PYTHON,
            version=ParserVersion(semver="1.0.0")
        ),
        ast_root=ast_root
    )


def build_fastapi_sample_files() -> dict[str, str]:
    return {
        "app/main.py": """
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from app.core.config import settings
from app.api.v1.endpoints import users, auth, items
from app.db.session import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(items.router, prefix="/items", tags=["items"])

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": settings.VERSION}
""",
        "app/core/config.py": """
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Service"
    VERSION: str = "2.4.0"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "supersecretkey"

settings = Settings()
""",
        "app/db/session.py": """
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
""",
        "app/models/user.py": """
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
""",
        "app/models/item.py": """
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
""",
        "app/schemas/user.py": """
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
""",
        "app/schemas/item.py": """
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ItemBase(BaseModel):
    title: str
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class ItemResponse(ItemBase):
    id: int
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True
""",
        "app/crud/user.py": """
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate

class CRUDUser:
    def get_by_id(self, db: Session, user_id: int) -> User:
        return db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, db: Session, email: str) -> User:
        return db.query(User).filter(User.email == email).first()

    def create(self, db: Session, obj_in: UserCreate) -> User:
        db_user = User(
            email=obj_in.email,
            hashed_password=obj_in.password,
            is_active=obj_in.is_active,
            is_superuser=obj_in.is_superuser
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

crud_user = CRUDUser()
""",
        "app/api/v1/endpoints/users.py": """
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud.user import crud_user
from app.schemas.user import UserResponse, UserCreate

router = APIRouter()

@router.post("/", response_model=UserResponse)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    user = crud_user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud_user.create(db, obj_in=user_in)

@router.get("/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = crud_user.get_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
""",
        "app/api/v1/endpoints/auth.py": """
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud.user import crud_user

router = APIRouter()

@router.post("/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = crud_user.get_by_email(db, email=email)
    if not user or user.hashed_password != password:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    return {"access_token": "token_123", "token_type": "bearer"}
""",
        "app/api/v1/endpoints/items.py": """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db

router = APIRouter()

@router.get("/")
def read_items(db: Session = Depends(get_db)):
    return []
"""
    }


def run_fastapi_benchmark():
    print("=" * 80)
    print("DEVBRAIN REPOSITORY ANALYZER V2 - REAL-WORLD FASTAPI BENCHMARK")
    print("=" * 80)

    sample_files = build_fastapi_sample_files()
    print(f"\n[1/3] Parsing {len(sample_files)} Python modules in FastAPI application...")

    parser_results = []
    parse_start = time.perf_counter()
    for file_path, source_code in sample_files.items():
        res = parse_source_file(source_code, file_path)
        parser_results.append(res)
    parse_duration = (time.perf_counter() - parse_start) * 1000.0

    print(f"      Parsed {len(parser_results)} modules in {parse_duration:.2f} ms")

    print("\n[2/3] Executing DependencyGraphFacade.analyze_repository pipeline...")
    analysis_start = time.perf_counter()
    result = DependencyGraphFacade.analyze_repository(
        parser_results=parser_results,
        repository_id="fastapi-enterprise-service"
    )
    analysis_duration = (time.perf_counter() - analysis_start) * 1000.0

    print("\n[3/3] Analysis Pipeline Completed Successfully!")
    print("=" * 80)
    print("BENCHMARK METRICS SUMMARY:")
    print("=" * 80)
    print(f"  Repository ID         : {result.repository_id}")
    print(f"  Schema SemVer         : {result.version}")
    print(f"  Total Duration        : {result.duration_ms:.2f} ms")
    print(f"  Canonical Symbols     : {len(result.semantic_repository.canonical_symbols.symbols)}")
    print(f"  Total Dependency Edges: {len(result.graph.edges)}")
    print(f"  Graph Density         : {result.graph.statistics.graph_density:.6f}")

    print("\n  Edge Kind Breakdown:")
    for edge_kind, count in result.graph.statistics.edges_by_kind_counts.items():
        print(f"    - {edge_kind:<20}: {count}")

    print("\n  Validation Report:")
    print(f"    - Status            : {'PASSED' if result.validation_report.is_valid else 'FAILED'}")
    print(f"    - SHA-256 Hash      : {result.validation_report.validated_graph_hash}")
    print(f"    - Evaluated Rules   : {result.validation_report.statistics.rules_evaluated_count}")
    print(f"    - Errors            : {result.validation_report.error_count}")
    print(f"    - Warnings          : {result.validation_report.warning_count}")
    print("=" * 80)


if __name__ == "__main__":
    run_fastapi_benchmark()
