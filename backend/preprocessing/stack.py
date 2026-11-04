"""
Xarray temporal stacks via Rioxarray.

Builds deterministic time-series cubes per AOI and collection.
"""

from pathlib import Path

import numpy as np
import rioxarray as rxr
import xarray as xr

from backend.shared.logging import get_logger

logger = get_logger(__name__)


def _load_band(path: Path) -> xr.DataArray:
    """Load single-band raster as DataArray (preserves CRS for rioxarray ops)."""
    da = rxr.open_rasterio(path, masked=True).squeeze(drop=True).load()
    if "band" in da.dims:
        da = da.squeeze("band", drop=True)
    return da.astype(np.float32)


def build_temporal_stack(
    raster_paths: list[tuple[str, Path]],
    output_path: Path,
) -> Path:
    """
    Stack normalized rasters along time dimension.

    raster_paths: list of (iso_datetime, path) sorted by time.
    """
    if not raster_paths:
        raise ValueError("No rasters provided for stack")

    times = [dt for dt, _ in raster_paths]
    ref = _load_band(raster_paths[0][1])
    arrays: list[xr.DataArray] = []

    for dt_str, path in raster_paths:
        da = _load_band(path)
        if path != raster_paths[0][1]:
            da = da.rio.reproject_match(ref).load()
        arrays.append(da)

    stacked = xr.concat(arrays, dim="time")
    stacked = stacked.assign_coords(time=np.array(times, dtype="U32"))
    stacked = stacked.drop_vars("spatial_ref", errors="ignore")
    stacked.name = "surface_reflectance"
    stacked.attrs["gs:stack_type"] = "temporal"
    stacked.attrs["gs:time_steps"] = len(times)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    stacked.to_netcdf(output_path, engine="netcdf4")
    logger.info("temporal_stack_saved", path=str(output_path), steps=len(times))
    return output_path
