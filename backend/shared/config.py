"""
Centralized application configuration.

Loads settings from environment variables via pydantic-settings.
Never hardcodes secrets; validates scope limits at startup.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with secure defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "GeoSentinel"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "geosentinel"
    postgres_user: str = "geosentinel"
    postgres_password: str = Field(default="change_me_in_production")

    data_root: Path = Field(
        default_factory=lambda: Path("/app/data") if Path("/app/data").exists() else Path(__file__).resolve().parents[2] / "data"
    )
    registry_path: Path = Field(
        default_factory=lambda: Path("/app/data/registry") if Path("/app/data/registry").exists() else Path(__file__).resolve().parents[2] / "data" / "registry"
    )

    max_aois: int = Field(default=3, ge=1, le=3)
    time_range_days: int = Field(default=30, ge=1, le=30)
    tile_size: int = Field(default=512, ge=256, le=512)
    update_frequency: Literal["weekly"] = "weekly"

    # Raster preprocessing (Phase 3)
    target_crs_epsg: int = Field(default=3857, ge=1024, le=32767)
    cloud_cover_threshold: float = Field(default=20.0, ge=0.0, le=100.0)
    raster_chunk_size: int = Field(default=512, ge=128, le=512)
    max_raster_pixels: int = Field(default=4096 * 4096, ge=65536)

    # Anomaly scoring thresholds (Phase 4 — rule-based)
    anomaly_ndvi_threshold: float = Field(default=0.15, ge=0.0, le=1.0)
    anomaly_ndwi_threshold: float = Field(default=0.12, ge=0.0, le=1.0)
    anomaly_nbr_threshold: float = Field(default=0.18, ge=0.0, le=1.0)
    anomaly_sar_threshold: float = Field(default=0.20, ge=0.0, le=10.0)
    anomaly_temporal_threshold: float = Field(default=0.10, ge=0.0, le=1.0)
    anomaly_composite_threshold: float = Field(default=0.45, ge=0.0, le=1.0)

    # OSINT (Phase 5)
    osint_live_fetch_enabled: bool = False
    osint_correlation_window_days: int = Field(default=7, ge=1, le=30)
    osint_max_events_per_source: int = Field(default=100, ge=1, le=500)
    osint_max_matches_per_aoi: int = Field(default=25, ge=1, le=100)
    firms_map_key: str | None = None
    acled_email: str | None = None
    acled_password: str | None = None

    # Explainability (Phase 6)
    explainability_png_width: int = Field(default=512, ge=128, le=1024)

    # Operational alerts (Phase 6)
    alert_low_geo_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    alert_high_geo_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    alert_medium_osint_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    alert_critical_osint_threshold: float = Field(default=0.65, ge=0.0, le=1.0)

    @field_validator("cors_origins")
    @classmethod
    def parse_cors(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("CORS_ORIGINS must not be empty")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def resolve_data_path(self, relative: str) -> Path:
        """Resolve a path under data_root; rejects traversal."""
        from backend.shared.security import safe_resolve_under

        return safe_resolve_under(self.data_root, relative)


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
