import type { AoiFeature, GeoJsonFeatureCollection, GeoJsonPolygon } from "../api/types";
import type { LatLngExpression } from "leaflet";

const DEFAULT_CENTER: LatLngExpression = [31.25, 34.8];

export function polygonCentroid(geometry: GeoJsonPolygon): LatLngExpression {
  const ring = geometry.coordinates[0];
  if (!ring?.length) return DEFAULT_CENTER;
  let latSum = 0;
  let lngSum = 0;
  const n = ring.length - 1;
  for (let i = 0; i < n; i++) {
    lngSum += ring[i][0];
    latSum += ring[i][1];
  }
  return [latSum / n, lngSum / n];
}

export function centerFromAoi(aoi: AoiFeature | null): LatLngExpression {
  if (!aoi) return DEFAULT_CENTER;
  return polygonCentroid(aoi.geometry);
}

export function centerFromBoundary(fc: GeoJsonFeatureCollection | null): LatLngExpression {
  const feat = fc?.features?.[0];
  if (feat?.geometry.type === "Polygon") {
    return polygonCentroid(feat.geometry);
  }
  return DEFAULT_CENTER;
}
