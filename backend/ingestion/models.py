"""
Pydantic models for ingestion configuration and results.

Validates curated manifest entries, AOI definitions, and ingest outcomes.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Platform(str, Enum):
    SENTINEL_1 = "sentinel-1"
    SENTINEL_2 = "sentinel-2"


class SourceType(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"


class LocalSource(BaseModel):
    type: Literal["local"] = "local"
    path: str = Field(..., description="Relative path under data_root")


class RemoteSource(BaseModel):
    type: Literal["remote"] = "remote"
    url: str = Field(..., max_length=2048)
    checksum_sha256: str = Field(..., min_length=64, max_length=64)

    @field_validator("url")
    @classmethod
    def https_only(cls, value: str) -> str:
        lowered = value.lower()
        if not lowered.startswith("https://"):
            raise ValueError("Remote source URL must use HTTPS")
        return value

    @field_validator("checksum_sha256")
    @classmethod
    def hex_lower(cls, value: str) -> str:
        if not all(c in "0123456789abcdef" for c in value.lower()):
            raise ValueError("checksum_sha256 must be hexadecimal")
        return value.lower()


class CuratedAsset(BaseModel):
    """Single curated imagery asset in the manifest."""

    id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")
    platform: Platform
    collection: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")
    aoi_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")
    datetime: datetime
    filename: str = Field(..., pattern=r"^[a-zA-Z0-9_.-]+$")
    bands: list[str] = Field(default_factory=list)
    polarization: str | None = None
    source: LocalSource | RemoteSource
    checksum_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    properties: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def checksum_required_for_remote(self) -> "CuratedAsset":
        if isinstance(self.source, RemoteSource):
            if self.checksum_sha256 and self.checksum_sha256 != self.source.checksum_sha256:
                raise ValueError("checksum_sha256 must match remote source checksum")
            self.checksum_sha256 = self.source.checksum_sha256
        elif self.checksum_sha256 is None:
            raise ValueError("Local assets require checksum_sha256 in manifest")
        return self


class CuratedManifest(BaseModel):
    version: str = "1"
    description: str = ""
    assets: list[CuratedAsset] = Field(default_factory=list)

    @field_validator("assets")
    @classmethod
    def unique_ids(cls, assets: list[CuratedAsset]) -> list[CuratedAsset]:
        ids = [a.id for a in assets]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate asset ids in manifest")
        return assets


class AOIRecord(BaseModel):
    aoi_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    geometry: dict[str, Any]
    active: bool = True

    @field_validator("geometry")
    @classmethod
    def polygon_feature(cls, geom: dict[str, Any]) -> dict[str, Any]:
        if geom.get("type") != "Polygon":
            raise ValueError("AOI geometry must be type Polygon")
        coords = geom.get("coordinates")
        if not coords or not isinstance(coords, list):
            raise ValueError("AOI Polygon coordinates required")
        return geom


class AOIConfig(BaseModel):
    version: str = "1"
    aois: list[AOIRecord] = Field(default_factory=list)

    @field_validator("aois")
    @classmethod
    def max_aois(cls, aois: list[AOIRecord]) -> list[AOIRecord]:
        if len(aois) > 3:
            raise ValueError("Maximum 3 AOIs allowed")
        ids = [a.aoi_id for a in aois]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate aoi_id values")
        return aois


class AssetIngestStatus(str, Enum):
    SKIPPED = "skipped"
    DOWNLOADED = "downloaded"
    COPIED = "copied"
    FAILED = "failed"


class AssetIngestResult(BaseModel):
    asset_id: str
    status: AssetIngestStatus
    message: str | None = None
    registry_item_id: str | None = None
    output_path: str | None = None


class IngestionResult(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime
    assets_total: int
    assets_ok: int
    assets_failed: int
    results: list[AssetIngestResult]
