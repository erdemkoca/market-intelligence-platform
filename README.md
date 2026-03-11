# Market Intelligence Platform

Swiss Construction Company Intelligence & Lead Engine.

Collects, enriches, and manages data about Swiss construction companies (Maler, Gipser, Fassaden) from official sources like Zefix/Handelsregister.

## Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), Alembic
- **Database**: PostgreSQL 16 with pg_trgm
- **Frontend**: Vue 3, TypeScript, Vite
- **Scheduler**: APScheduler
- **Deployment**: Docker Compose

## Quick Start

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Start everything
docker compose up -d

# 3. API is at http://localhost:8000
# 4. Dashboard is at http://localhost:3000
# 5. Trigger first Zefix import
curl -X POST http://localhost:8000/api/ingestion/zefix
```

## Local Development (without Docker)

```bash
# Start PostgreSQL (e.g. via Docker)
docker run -d --name mi-postgres -p 5432:5432 \
  -e POSTGRES_USER=mi_user -e POSTGRES_PASSWORD=mi_password \
  -e POSTGRES_DB=market_intelligence postgres:16-alpine

# Enable pg_trgm
docker exec mi-postgres psql -U mi_user -d market_intelligence -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# Install Python dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start API
uvicorn src.main:app --reload --port 8000

# Start scheduler (separate terminal)
python -m src.scheduler.jobs

# Start dashboard (separate terminal)
cd dashboard && npm install && npm run dev
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/companies` | List companies (with filters) |
| GET | `/api/companies/{id}` | Company detail |
| GET | `/api/companies/stats` | Aggregate statistics |
| GET | `/api/leads` | List leads |
| PATCH | `/api/leads/{id}` | Update lead |
| POST | `/api/leads/{id}/interactions` | Add interaction |
| POST | `/api/ingestion/zefix` | Trigger Zefix import |
| GET | `/api/ingestion/jobs` | List import jobs |
| GET | `/api/search?q=...` | Search companies |
| GET | `/api/health` | Health check |

## Data Sources

- **Zefix** (Zentraler Firmenindex): Swiss commercial register — searched by trade terms (Maler, Gipser, Fassade, etc.)
- **UID Register**: Company identification (planned)
- **SHAB**: Commercial gazette events (planned)

## Target NOGA Codes (Phase 1)

- `43.31` — Gipserei / Verputzerei / Stuckateur
- `43.34` — Malerei / Glaserei

## Scheduled Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| Zefix Sync | Daily 05:00 | Import companies from Zefix |
| Lead Scoring | Daily 08:00 | Recalculate lead scores |
