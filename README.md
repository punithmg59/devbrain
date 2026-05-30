# DevBrain

**DevBrain** is an AI Engineering Intelligence Platform that helps developers understand, validate, remember, and debug AI-generated software systems.

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | FastAPI (Python)                    |
| Frontend   | React + Vite + TypeScript           |
| Database   | PostgreSQL (hosted on Supabase)     |
| LLM        | Groq API                            |
| ORM        | SQLAlchemy 2.0 (async)              |
| Migrations | Alembic                             |
| Styling    | Tailwind CSS                        |

## Project Structure

```
devbrain/
├── backend/          # FastAPI application
│   ├── app/          # Application code
│   ├── alembic/      # Database migrations
│   └── requirements.txt
├── frontend/         # React + Vite application
└── README.md
```

## Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

Copy and fill in environment variables in `backend/.env` (see below).

Run the development server:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

Health check: `GET http://localhost:8000/health`

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

## Environment Variables

### Backend (`backend/.env`)

| Variable               | Description                              |
|------------------------|------------------------------------------|
| `DATABASE_URL`         | Async PostgreSQL URL (asyncpg driver)    |
| `DIRECT_URL`           | Sync PostgreSQL URL (for Alembic)        |
| `APP_URL`              | Backend URL                              |
| `FRONTEND_URL`         | Frontend URL (used for CORS)             |
| `SECRET_KEY`           | JWT/session signing key                  |
| `ENVIRONMENT`          | `development` or `production`            |
| `GITHUB_CLIENT_ID`     | GitHub OAuth app client ID               |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth app client secret           |
| `GROQ_API_KEY`         | Groq API key                             |
| `REDIS_URL`            | Redis connection URL                     |
| `SUPABASE_URL`         | Supabase project URL                     |
| `SUPABASE_ANON_KEY`    | Supabase anonymous key                   |
| `SENTRY_DSN`           | (Optional) Sentry error tracking DSN     |

### Frontend (`frontend/.env`)

| Variable        | Description        |
|-----------------|--------------------|
| `VITE_API_URL`  | Backend API URL    |
| `VITE_APP_NAME` | Application name   |

## Database Setup

### 1. Enable PostgreSQL extensions (Supabase SQL Editor)

Run this **before** migrations:

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "vector";
```

### 2. Run migrations

From the `backend/` directory, after filling in `DATABASE_URL` and `DIRECT_URL`:

```bash
alembic upgrade head
```

### 3. Add trigram indexes (after tables exist)

Run in the Supabase SQL Editor **after** migrations.  
**Important:** `pg_trgm` must be enabled first — otherwise you get `operator class "gin_trgm_ops" does not exist`.

```sql
-- Required before trigram indexes
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE INDEX IF NOT EXISTS idx_nodes_name_trgm
  ON nodes USING GIN (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_files_path_trgm
  ON repo_files USING GIN (file_path gin_trgm_ops);
```

## API Endpoints

| Method | Path      | Description              |
|--------|-----------|--------------------------|
| GET    | `/health` | Health check             |

## License

Proprietary — DevBrain
