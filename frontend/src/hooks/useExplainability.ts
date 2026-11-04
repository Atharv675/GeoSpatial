import { useCallback, useEffect, useState } from "react";
import {
  fetchArtifactGeoJson,
  fetchManifest,
  isNotFound,
} from "../api/client";
import type {
  ExplainabilityManifest,
  GeoJsonFeatureCollection,
} from "../api/types";

export interface OverlayLayers {
  boundary: GeoJsonFeatureCollection | null;
  anomaly: GeoJsonFeatureCollection | null;
  osint: GeoJsonFeatureCollection | null;
}

export interface UseExplainabilityResult {
  manifest: ExplainabilityManifest | null;
  overlays: OverlayLayers;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

function findArtifactPath(
  manifest: ExplainabilityManifest,
  name: string
): string | undefined {
  return manifest.artifacts.find((a) => a.name === name)?.path;
}

export function useExplainability(aoiId: string | null): UseExplainabilityResult {
  const [manifest, setManifest] = useState<ExplainabilityManifest | null>(null);
  const [overlays, setOverlays] = useState<OverlayLayers>({
    boundary: null,
    anomaly: null,
    osint: null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!aoiId) {
      setManifest(null);
      setOverlays({ boundary: null, anomaly: null, osint: null });
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const m = await fetchManifest(aoiId);
      setManifest(m);

      const loadLayer = async (name: string) => {
        const path = findArtifactPath(m, name);
        if (!path) return null;
        try {
          return await fetchArtifactGeoJson(aoiId, path);
        } catch {
          return null;
        }
      };

      const [boundary, anomaly, osint] = await Promise.all([
        loadLayer("aoi_boundary"),
        loadLayer("anomaly_summary"),
        loadLayer("osint_markers"),
      ]);
      setOverlays({ boundary, anomaly, osint });
    } catch (e) {
      if (isNotFound(e)) {
        setError("No explainability run yet. Run generate_visuals on the backend.");
      } else {
        setError("Failed to load explainability data.");
      }
      setManifest(null);
      setOverlays({ boundary: null, anomaly: null, osint: null });
    } finally {
      setLoading(false);
    }
  }, [aoiId]);

  useEffect(() => {
    load();
  }, [load]);

  return { manifest, overlays, loading, error, reload: load };
}
