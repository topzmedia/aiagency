# Content Finder

A keyword-driven multimodal video content finder for short-form public videos.

Content Finder allows users to search, analyze, rank, and organize video content from compliant/authorized sources using natural-language queries. The system uses multimodal AI analysis including object detection, scene classification, OCR, speech-to-text, and semantic embeddings to find relevant video content.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Next.js    │────▶│   FastAPI     │────▶│  PostgreSQL  │
│   Frontend   │     │   Backend     │     │  + pgvector  │
│   :3000      │     │   :8000       │     │  :5432       │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────▼───────┐     ┌──────────────┐
                    │    Celery     │────▶│    Redis      │
                    │    Workers    │     │    :6379      │
                    └──────────────┘     └──────────────┘
```

### Monorepo Structure

```
/apps/web          - Next.js 15 frontend (TypeScript, Tailwind, shadcn/ui)
/apps/api          - FastAPI backend (Python 3.11+, SQLAlchemy 2.x)
/workers           - Celery background workers
/scripts           - Seed and utility scripts
/data/seed         - Demo seed data (sample CSV)
/data/ingest       - Ingestion input directory
/data/media        - Local media storage
/data/exports      - Export output directory
/infra             - Infrastructure configs
/tests             - Backend test suite
```

## Prerequisites

- Docker and Docker Compose (v2+)
- Make (optional, for convenience targets)
- Git

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env if needed (defaults work for local dev)
```

### 2. Start all services

```bash
docker compose up --build -d
# or
make up
```

This starts: PostgreSQL (with pgvector), Redis, FastAPI backend, Celery worker, and Next.js frontend.

### 3. Run database migrations

```bash
docker compose exec api alembic upgrade head
# or
make migrate
```

### 4. Seed demo data

```bash
docker compose exec api python -m scripts.seed
# or
make seed
```

This creates:
- A default user (demo@contentfinder.dev)
- 15 sample candidate videos across 5 content categories
- Video analyses with realistic detection/classification data
- A sample search ("car crash dashcam footage") with ranked results
- A sample collection

### 5. Access the app

- **Frontend**: http://localhost:3000
- **API docs**: http://localhost:8000/docs (Swagger UI)
- **Health check**: http://localhost:8000/health

## How to Use

### Creating a Search

1. Go to the Dashboard or Searches page
2. Click "New Search" or use the Quick Search bar
3. Enter a natural-language query (e.g., "car crashes", "luxury kitchens", "dogs playing in snow")
4. Optionally configure: platforms, region, language, date range, filters, confidence threshold
5. Click "Launch Search"
6. The search is queued and processed by background workers
7. Results appear on the Search Detail page with scores and explanations

### Ingesting Content

The system supports multiple ingestion adapters:

**CSV Import:**
```bash
# Place a CSV file in /data/ingest/ or use the Ingestion page
# CSV columns: source_url, platform, creator_handle, caption_text, hashtags, publish_date, language, region_hint, duration_sec
```

**Local Folder:**
- Drop mp4/mov/webm files into `/data/ingest/`
- Create an ingestion job with source_type "local_folder"

**Demo Seed:**
- Create an ingestion job with source_type "demo_seed" for built-in sample data

### Viewing Results

Each result shows:
- Relevance score with breakdown
- Reason codes explaining why it matched
- Matched temporal segments
- Platform, creator, caption info
- Feedback buttons (Very Relevant / Somewhat Relevant / Irrelevant)

### Exporting

- Click "Export CSV" or "Export JSON" on any completed search
- Exports include: rank, score, source_url, platform, creator, caption, reason codes, etc.

### Collections

- Save interesting results to named collections
- Add notes to collection items
- Browse collections from the Collections page

## Running Tests

```bash
docker compose exec api pytest tests/ -v
# or
make test
```

Test coverage includes:
- Query interpretation (synonym expansion, entity extraction)
- Scoring engine (weighted scoring, reason codes, thresholds)
- Deduplication grouping
- CSV ingestion parsing
- API endpoint integration tests

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/searches | Create a new search |
| GET | /api/searches | List all searches |
| GET | /api/searches/{id} | Get search details |
| GET | /api/searches/{id}/results | Get ranked results |
| POST | /api/searches/{id}/rerank | Re-rank results |
| GET | /api/searches/{id}/export.csv | Export results as CSV |
| GET | /api/searches/{id}/export.json | Export results as JSON |
| GET | /api/results/{id} | Get result details |
| POST | /api/results/{id}/feedback | Submit feedback |
| GET | /api/results/{id}/explain | Get score explanation |
| POST | /api/collections | Create collection |
| GET | /api/collections | List collections |
| GET | /api/collections/{id} | Get collection |
| POST | /api/collections/{id}/items | Add item to collection |
| DELETE | /api/collections/{id}/items/{item_id} | Remove item |
| POST | /api/ingestion/jobs | Create ingestion job |
| GET | /api/ingestion/jobs | List ingestion jobs |
| GET | /api/ingestion/jobs/{id} | Get job details |
| GET | /health | Health check |

Full OpenAPI documentation available at http://localhost:8000/docs

## Search Pipeline

1. **Query Interpretation** - Parse natural language into structured entities, actions, scenes, synonyms
2. **Candidate Retrieval** - Get candidates from DB, apply platform/date/region/language filters
3. **Cheap Prefilter** - Keyword match on captions/hashtags to reduce candidate set
4. **Deep Analysis** - Run multimodal analysis pipeline (OCR, ASR, object detection, scene classification)
5. **Scoring** - Weighted multi-dimensional scoring with configurable weights
6. **Deduplication** - Group near-duplicates by caption/content similarity
7. **Ranking** - Sort by score, apply confidence threshold, persist results

## Scoring Weights

| Dimension | Weight |
|-----------|--------|
| Caption similarity | 0.12 |
| Hashtag similarity | 0.08 |
| OCR similarity | 0.12 |
| Transcript similarity | 0.15 |
| Visual object score | 0.18 |
| Visual scene score | 0.12 |
| Action/event score | 0.18 |
| Audio event score | 0.05 |
| Quality score | 0.05 |

## Configuration

All configuration via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | postgresql+asyncpg://... | PostgreSQL connection |
| REDIS_URL | redis://redis:6379/0 | Redis connection |
| STORAGE_MODE | local | Storage backend (local/s3) |
| LOCAL_MEDIA_ROOT | /data/media | Local media directory |
| INGEST_ROOT | /data/ingest | Ingestion input directory |
| EMBEDDING_MODEL_NAME | all-MiniLM-L6-v2 | Sentence transformer model |
| WHISPER_MODEL_SIZE | base | Whisper ASR model size |
| OCR_PROVIDER | easyocr | OCR engine |
| LOG_LEVEL | INFO | Logging level |
| APP_ENV | development | Environment name |

## Known Limitations

- **MVP Analysis Pipeline**: Object detection and scene classification use heuristic-based implementations. The interfaces support upgrading to real ML models.
- **No Auth**: Single-user mode with no authentication for local development.
- **Local Storage Only**: Media files stored locally. S3 abstraction layer is stubbed for future production use.
- **Embedding Models**: Require downloading on first use (~90MB for all-MiniLM-L6-v2).
- **No Real-Time Streaming**: Search progress is polled, not streamed via WebSocket.

## Compliance Note

This application is designed for **compliant discovery, analysis, ranking, and organization** of public/authorized content.

It does **NOT**:
- Remove watermarks from any content
- Bypass platform protections or rate limits
- Bulk download unauthorized media
- Implement stealth scraping or anti-detection behavior
- Claim access to all content on any platform

The ingestion system uses an adapter pattern so compliant source adapters (authorized APIs, licensed feeds) can be added without modifying the core application.

## Tech Stack

- **Frontend**: Next.js 15, TypeScript, Tailwind CSS, shadcn/ui, React Query
- **Backend**: Python 3.11+, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic
- **Workers**: Celery, Redis
- **Database**: PostgreSQL 16 with pgvector
- **Media**: FFmpeg, OpenCV
- **ML/AI**: sentence-transformers, EasyOCR, faster-whisper
- **Infra**: Docker, Docker Compose
