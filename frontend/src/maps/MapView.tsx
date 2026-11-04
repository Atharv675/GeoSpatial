import { useMemo } from "react";
import { MapContainer, TileLayer } from "react-leaflet";
import type { LatLngExpression } from "leaflet";
import "leaflet/dist/leaflet.css";
import type { GeoJsonFeatureCollection } from "../api/types";
import MapOverlays, { type LayerVisibility } from "../overlays/MapOverlays";
import FitBounds from "./FitBounds";
import { centerFromBoundary } from "./geoUtils";

interface MapViewProps {
  boundary: GeoJsonFeatureCollection | null;
  anomaly: GeoJsonFeatureCollection | null;
  osint: GeoJsonFeatureCollection | null;
  layers: LayerVisibility;
  fallbackCenter?: LatLngExpression;
}

export default function MapView({
  boundary,
  anomaly,
  osint,
  layers,
  fallbackCenter = [31.25, 34.8],
}: MapViewProps) {
  const center = useMemo(
    () => centerFromBoundary(boundary) ?? fallbackCenter,
    [boundary, fallbackCenter]
  );

  return (
    <MapContainer
      center={center}
      zoom={11}
      style={{ height: "100%", width: "100%" }}
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitBounds data={boundary} />
      <MapOverlays
        layers={layers}
        boundary={boundary}
        anomaly={anomaly}
        osint={osint}
      />
    </MapContainer>
  );
}
