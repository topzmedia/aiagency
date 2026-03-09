"""API integration tests for Content Finder endpoints."""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Health endpoint should return ok status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_create_search(client):
    """POST /searches/ should create a new search."""
    payload = {
        "raw_query": "car crash dashcam footage",
        "max_results": 20,
        "confidence_threshold": 0.3,
    }
    resp = await client.post("/searches/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["raw_query"] == "car crash dashcam footage"
    assert data["status"] == "queued"
    assert data["max_results"] == 20
    assert "id" in data


@pytest.mark.asyncio
async def test_list_searches(client):
    """GET /searches/ should return paginated search list."""
    # Create a search first
    payload = {"raw_query": "test search query"}
    await client.post("/searches/", json=payload)

    resp = await client.get("/searches/")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_search_not_found(client):
    """GET /searches/{id} should return 404 for non-existent search."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/searches/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_collection(client):
    """POST /collections/ should create a new collection."""
    payload = {
        "name": "Test Collection",
        "description": "A test collection for unit tests",
    }
    resp = await client.post("/collections/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Collection"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_collections(client):
    """GET /collections/ should return list of collections."""
    # Create one first
    await client.post("/collections/", json={"name": "List Test"})

    resp = await client.get("/collections/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_create_ingestion_job(client):
    """POST /ingestion/jobs should create a new ingestion job."""
    payload = {
        "source_type": "csv",
        "source_config": {"file_path": "/data/seed/sample_videos.csv"},
    }
    resp = await client.post("/ingestion/jobs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_type"] == "csv"
    assert data["status"] == "queued"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_ingestion_jobs(client):
    """GET /ingestion/jobs should return list of ingestion jobs."""
    # Create one first
    await client.post(
        "/ingestion/jobs",
        json={"source_type": "csv", "source_config": {}},
    )

    resp = await client.get("/ingestion/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_search_by_id(client):
    """GET /searches/{id} should return search details after creation."""
    create_resp = await client.post(
        "/searches/",
        json={"raw_query": "dogs playing in snow"},
    )
    search_id = create_resp.json()["id"]

    resp = await client.get(f"/searches/{search_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == search_id
    assert data["raw_query"] == "dogs playing in snow"


@pytest.mark.asyncio
async def test_create_search_validation(client):
    """POST /searches/ with empty query should fail validation."""
    payload = {"raw_query": ""}
    resp = await client.post("/searches/", json=payload)
    assert resp.status_code == 422
