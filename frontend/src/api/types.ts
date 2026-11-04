/** GeoSentinel API types — aligned with backend Pydantic models. */

export interface GeoJsonPolygon {
  type: "Polygon";
  coordinates: number[][][];
}

export interface GeoJsonFeature {
  type: "Feature";
  properties?: Record<string, unknown>;
  geometry: GeoJsonPolygon | { type: "Point"; coordinates: [number, number] };
}

export interface GeoJsonFeatureCollection {
  type: "FeatureCollection";
  features: GeoJsonFeature[];
}

export interface AoiFeature {
  type: "Feature";
  properties: {
    aoi_id: string;
    name: string;
    description?: string;
    active?: boolean;
  };
  geometry: GeoJsonPolygon;
}

export interface AoiCollection {
  type: "FeatureCollection";
  features: AoiFeature[];
  count: number;
  max_allowed: number;
}

export type ArtifactType =
  | "heatmap"
  | "overlay"
  | "before_after"
  | "confidence"
  | "timeline";

export interface ExplainabilityArtifact {
  type: ArtifactType;
  aoi_id: string;
  name: string;
  path: string;
  description: string;
  metadata?: Record<string, unknown>;
}

export interface TimelineEvent {
  datetime: string;
  label: string;
  category: string;
  score?: number | null;
  source?: string | null;
}

export interface ConfidenceBreakdown {
  aoi_id: string;
  summary?: string;
  geospatial: Record<string, unknown>;
  osint: Record<string, unknown>;
  fusion: Record<string, unknown>;
}

export interface ExplainabilityManifest {
  aoi_id: string;
  run_id: string;
  artifacts: ExplainabilityArtifact[];
  timeline: TimelineEvent[];
  confidence_breakdown: ConfidenceBreakdown;
}

export interface OperationalAlert {
  alert_id: string;
  aoi_id: string;
  severity: "low" | "medium" | "high" | "critical";
  title: string;
  summary: string;
  geospatial_score: number;
  osint_fusion_score: number;
  is_anomaly: boolean;
}

export interface AlertsLastRun {
  run_id: string;
  alerts: OperationalAlert[];
}

export interface ExplainabilityStatus {
  has_run: boolean;
  last_run?: {
    run_id: string;
    artifacts_total: number;
    bundles?: { aoi_id: string }[];
  };
}
