# Seed Data

This directory contains sample data for bootstrapping the Content Finder database.

## Files

- **sample_videos.csv** - 15 sample candidate video records covering diverse content categories:
  - Car crash / dashcam footage (5 videos)
  - Luxury kitchen tours (3 videos)
  - Dogs playing in snow (3 videos)
  - People arguing in public (2 videos)
  - Smiling couple at kitchen table (3 videos, including a near-duplicate variant)

## Usage

### Option 1: Full seed (recommended for first setup)

```bash
make seed
# or
docker compose exec api python -m scripts.seed
```

This creates a default user, imports all sample videos, generates analyses, and creates a sample search with ranked results.

### Option 2: Demo ingestion only

```bash
make ingest-demo
# or
docker compose exec api python -m scripts.ingest_demo
```

This creates an ingestion job and processes the CSV through the ingestion pipeline (either via Celery worker or synchronously as fallback).

## Customization

To add more seed data, add rows to `sample_videos.csv`. Required columns:
- `source_url` (must be unique)
- `platform`

All other columns are optional.
