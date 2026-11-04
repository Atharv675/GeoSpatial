"""
512×512 tiled output via Rasterio windowed reads (chunked, memory-safe).
"""

from pathlib import Path

import rasterio
from rasterio.windows import Window

from backend.shared.config import get_settings
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def generate_tiles(src_path: Path, output_dir: Path, tile_size: int | None = None) -> list[str]:
    """
    Split raster into fixed-size tiles.

    Returns list of relative tile filenames written.
    """
    settings = get_settings()
    size = tile_size or settings.tile_size
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    with rasterio.open(src_path) as src:
        profile = src.profile.copy()
        profile.update(height=size, width=size, compress="deflate")
        block = (min(size, 256) // 16) * 16
        if block >= 16:
            profile.update(tiled=True, blockxsize=block, blockysize=block)

        for row in range(0, src.height, size):
            for col in range(0, src.width, size):
                win = Window(col, row, min(size, src.width - col), min(size, src.height - row))
                if win.width == 0 or win.height == 0:
                    continue
                data = src.read(1, window=win)
                tile_name = f"tile_{row // size}_{col // size}.tif"
                tile_path = output_dir / tile_name
                tile_profile = profile.copy()
                tile_profile.update(height=win.height, width=win.width)
                with rasterio.open(tile_path, "w", **tile_profile) as dst:
                    dst.write(data, 1)
                written.append(tile_name)

    logger.info("tiles_generated", src=str(src_path), count=len(written), tile_size=size)
    return written
