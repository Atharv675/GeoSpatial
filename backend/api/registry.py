"""Metadata registry API — STAC-compatible lightweight catalog."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.shared.exceptions import GeoSentinelError, ValidationError
from backend.storage.registry import MetadataRegistry

router = APIRouter(prefix="/registry", tags=["registry"])


class RegistryItemCreate(BaseModel):
    """Minimal STAC Item payload for registration."""

    id: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$")
    properties: dict[str, Any] = Field(default_factory=dict)
    assets: dict[str, Any] = Field(default_factory=dict)
    geometry: dict[str, Any] | None = None
    bbox: list[float] | None = None


@router.get("/items")
async def list_registry_items() -> dict[str, Any]:
    """List all registered imagery/metadata items."""
    reg = MetadataRegistry()
    items = reg.list_items()
    return {"count": len(items), "items": items}


@router.get("/items/{item_id}")
async def get_registry_item(item_id: str) -> dict[str, Any]:
    """Get a single registry item by id."""
    reg = MetadataRegistry()
    item = reg.get_item(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def register_item(payload: RegistryItemCreate) -> dict[str, Any]:
    """Register a STAC-compatible item (curated assets only)."""
    item_dict: dict[str, Any] = {
        "type": "Item",
        "stac_version": "1.0.0",
        "id": payload.id,
        "properties": payload.properties,
        "assets": payload.assets,
    }
    if payload.geometry:
        item_dict["geometry"] = payload.geometry
    if payload.bbox:
        item_dict["bbox"] = payload.bbox

    try:
        reg = MetadataRegistry()
        return reg.register_item(item_dict)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)
    except GeoSentinelError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message)
