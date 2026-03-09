from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database import get_db
from apps.api.models.collection import Collection, CollectionItem
from apps.api.schemas.collection import (
    CollectionCreate,
    CollectionItemCreate,
    CollectionItemResponse,
    CollectionResponse,
)

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(payload: CollectionCreate, db: AsyncSession = Depends(get_db)) -> dict:
    collection = Collection(
        name=payload.name,
        description=payload.description,
        user_id=payload.user_id,
    )
    db.add(collection)
    await db.flush()
    await db.refresh(collection)
    return {
        "id": collection.id,
        "user_id": collection.user_id,
        "name": collection.name,
        "description": collection.description,
        "created_at": collection.created_at,
        "updated_at": collection.updated_at,
        "item_count": 0,
    }


@router.get("", response_model=list[CollectionResponse])
async def list_collections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    query = select(Collection).order_by(Collection.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    collections = list(result.scalars().all())

    response = []
    for c in collections:
        count_result = await db.execute(
            select(func.count()).select_from(CollectionItem).where(CollectionItem.collection_id == c.id)
        )
        item_count = count_result.scalar_one()
        response.append({
            "id": c.id,
            "user_id": c.user_id,
            "name": c.name,
            "description": c.description,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "item_count": item_count,
        })
    return response


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

    count_result = await db.execute(
        select(func.count()).select_from(CollectionItem).where(CollectionItem.collection_id == collection.id)
    )
    item_count = count_result.scalar_one()

    return {
        "id": collection.id,
        "user_id": collection.user_id,
        "name": collection.name,
        "description": collection.description,
        "created_at": collection.created_at,
        "updated_at": collection.updated_at,
        "item_count": item_count,
    }


@router.post(
    "/{collection_id}/items",
    response_model=CollectionItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_collection_item(
    collection_id: uuid.UUID,
    payload: CollectionItemCreate,
    db: AsyncSession = Depends(get_db),
) -> CollectionItem:
    result = await db.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

    item = CollectionItem(
        collection_id=collection_id,
        candidate_video_id=payload.candidate_video_id,
        notes=payload.notes,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/{collection_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection_item(
    collection_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(CollectionItem).where(
            CollectionItem.id == item_id,
            CollectionItem.collection_id == collection_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection item not found")

    await db.delete(item)
    await db.flush()
