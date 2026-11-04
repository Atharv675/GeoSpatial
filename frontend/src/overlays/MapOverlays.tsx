import { CircleMarker, GeoJSON, Popup } from "react-leaflet";
import type { GeoJsonFeatureCollection } from "../api/types";
import { anomalyStyle, boundaryStyle, osintPointStyle } from "./mapStyles";

export interface LayerVisibility {
  boundary: boolean;
  anomaly: boolean;
  osint: boolean;
}

interface MapOverlaysProps {
  layers: LayerVisibility;
  boundary: GeoJsonFeatureCollection | null;
  anomaly: GeoJsonFeatureCollection | null;
  osint: GeoJsonFeatureCollection | null;
}

export default function MapOverlays({
  layers,
  boundary,
  anomaly,
  osint,
}: MapOverlaysProps) {
  return (
    <>
      {layers.boundary && boundary && boundary.features.length > 0 && (
        <GeoJSON key="boundary" data={boundary} style={() => boundaryStyle} />
      )}
      {layers.anomaly && anomaly && anomaly.features.length > 0 && (
        <GeoJSON
          key="anomaly"
          data={anomaly}
          style={(feature) => anomalyStyle(feature as Parameters<typeof anomalyStyle>[0])}
        />
      )}
      {layers.osint &&
        osint &&
        osint.features.map((f, i) => {
          if (f.geometry.type !== "Point") return null;
          const [lng, lat] = f.geometry.coordinates as [number, number];
          const props = f.properties ?? {};
          return (
            <CircleMarker
              key={`osint-${props.event_id ?? i}`}
              center={[lat, lng]}
              radius={osintPointStyle.radius}
              pathOptions={{
                fillColor: osintPointStyle.fillColor,
                color: osintPointStyle.color,
                weight: osintPointStyle.weight,
                fillOpacity: osintPointStyle.fillOpacity,
              }}
            >
              <Popup>
                <strong>{String(props.title ?? "OSINT event")}</strong>
                <br />
                <span style={{ fontSize: "0.85em" }}>
                  {String(props.source ?? "")} · conf{" "}
                  {Number(props.confidence ?? 0).toFixed(2)}
                </span>
                {props.explanation ? (
                  <>
                    <br />
                    <em style={{ fontSize: "0.8em" }}>{String(props.explanation)}</em>
                  </>
                ) : null}
              </Popup>
            </CircleMarker>
          );
        })}
    </>
  );
}
