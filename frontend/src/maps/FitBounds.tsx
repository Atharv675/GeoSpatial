import { useEffect } from "react";
import L from "leaflet";
import { useMap } from "react-leaflet";
import type { GeoJsonFeatureCollection } from "../api/types";

interface FitBoundsProps {
  data: GeoJsonFeatureCollection | null;
}

/** Fit map viewport to AOI boundary when it loads or changes. */
export default function FitBounds({ data }: FitBoundsProps) {
  const map = useMap();

  useEffect(() => {
    if (!data?.features?.length) return;
    const layer = L.geoJSON(data as GeoJSON.GeoJsonObject);
    const bounds = layer.getBounds();
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [32, 32], maxZoom: 12 });
    }
  }, [data, map]);

  return null;
}
