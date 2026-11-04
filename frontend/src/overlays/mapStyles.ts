import type { PathOptions } from "leaflet";

export const boundaryStyle: PathOptions = {
  color: "#3d8bfd",
  weight: 2,
  fillOpacity: 0.08,
  fillColor: "#3d8bfd",
};

export function anomalyStyle(feature?: { properties?: Record<string, unknown> }): PathOptions {
  const score = Number(feature?.properties?.composite_score ?? 0);
  const isAnomaly = Boolean(feature?.properties?.is_anomaly);
  const hue = isAnomaly ? 0 : 200;
  const alpha = Math.min(0.55, 0.2 + score * 0.5);
  return {
    color: isAnomaly ? "#e85d4c" : "#5bc0be",
    weight: 2,
    fillColor: `hsl(${hue}, 70%, 45%)`,
    fillOpacity: alpha,
  };
}

export const osintPointStyle = {
  radius: 7,
  fillColor: "#f0ad4e",
  color: "#fff",
  weight: 1,
  fillOpacity: 0.9,
};
