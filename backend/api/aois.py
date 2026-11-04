"""AOI configuration API."""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from backend.ingestion.aoi import aoi_to_feature, get_aoi, load_aoi_config
from backend.shared.exceptions import ConfigurationError, ValidationError

router = APIRouter(prefix="/aois", tags=["aois"])


@router.get("")
async def list_aois() -> dict[str, Any]:
    """List configured areas of interest as GeoJSON FeatureCollection."""
    try:
        config = load_aoi_config()
    except (ConfigurationError, ValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message)

    features = [aoi_to_feature(a) for a in config.aois if a.active]
    return {
        "type": "FeatureCollection",
        "features": features,
        "count": len(features),
        "max_allowed": 3,
    }


@router.get("/{aoi_id}")
async def get_aoi_detail(aoi_id: str) -> dict[str, Any]:
    """Get single AOI by id."""
    aoi = get_aoi(aoi_id)
    if not aoi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AOI not found")
    return aoi_to_feature(aoi)
