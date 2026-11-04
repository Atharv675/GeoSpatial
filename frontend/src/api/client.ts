/**
 * GeoSentinel API client — no secrets in frontend; env-based base URL only.
 */

import type {
  AlertsLastRun,
  AoiCollection,
  ExplainabilityManifest,
  ExplainabilityStatus,
  GeoJsonFeatureCollection,
} from "./types";

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    headers: { Accept: "application/json", ...init?.headers },
    credentials: "same-origin",
    ...init,
  });
  if (!res.ok) {
    const err = new Error(`API error ${res.status}`) as Error & { status: number };
    err.status = res.status;
    throw err;
  }
  return res.json() as Promise<T>;
}

export function isNotFound(err: unknown): boolean {
  return (err as { status?: number })?.status === 404;
}

export interface HealthResponse {
  status: string;
}

export interface ReadyResponse {
  status: string;
  database: boolean;
  registry: boolean;
  app: string;
  scope?: {
    max_aois: number;
    time_range_days: number;
    tile_size: number;
  };
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function fetchReady(): Promise<ReadyResponse> {
  return request<ReadyResponse>("/ready");
}

export function fetchAois(): Promise<AoiCollection> {
  return request<AoiCollection>("/aois");
}

export function fetchExplainabilityStatus(): Promise<{
  has_run: boolean;
  last_run?: ExplainabilityStatus["last_run"];
}> {
  return request("/explainability/status");
}

export function fetchManifest(
  aoiId: string,
  runId?: string
): Promise<ExplainabilityManifest> {
  const q = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return request<ExplainabilityManifest>(`/explainability/${aoiId}/manifest${q}`);
}

/** URL for PNG/GeoJSON artifact (img src or fetch). */
export function artifactUrl(aoiId: string, relativePath: string): string {
  return `${API_BASE}/explainability/${aoiId}/artifact?path=${encodeURIComponent(relativePath)}`;
}

export async function fetchArtifactGeoJson<T = GeoJsonFeatureCollection>(
  aoiId: string,
  relativePath: string
): Promise<T> {
  const url = artifactUrl(aoiId, relativePath);
  const res = await fetch(url, { credentials: "same-origin" });
  if (!res.ok) {
    const err = new Error(`Artifact error ${res.status}`) as Error & { status: number };
    err.status = res.status;
    throw err;
  }
  return res.json() as Promise<T>;
}

export function fetchAlertsStatus(): Promise<{
  has_run: boolean;
  last_run: AlertsLastRun | null;
}> {
  return request("/alerts/status");
}

export function fetchRegistryItems(): Promise<{ count: number; items: unknown[] }> {
  return request("/registry/items");
}
