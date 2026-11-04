"""
Spatial matching: point-in-polygon and AOI bbox checks.
"""

from typing import Any


def point_in_polygon(lon: float, lat: float, polygon_coords: list[list[float]]) -> bool:
    """
    Ray-casting algorithm for GeoJSON Polygon outer ring.

    polygon_coords: list of [lon, lat] vertices.
    """
    n = len(polygon_coords)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon_coords[i][0], polygon_coords[i][1]
        xj, yj = polygon_coords[j][0], polygon_coords[j][1]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


def spatial_score_for_point(
    lon: float,
    lat: float,
    aoi_geometry: dict[str, Any],
    bbox: list[float],
) -> float:
    """
    Score spatial relevance: 1.0 inside polygon, 0.5 in bbox only, 0.0 outside.
    """
    if aoi_geometry.get("type") == "Polygon":
        ring = aoi_geometry["coordinates"][0]
        if point_in_polygon(lon, lat, ring):
            return 1.0
    west, south, east, north = bbox
    if west <= lon <= east and south <= lat <= north:
        return 0.5
    return 0.0
