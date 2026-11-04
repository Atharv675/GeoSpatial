import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { fetchAois, fetchAlertsStatus, fetchExplainabilityStatus } from "../api/client";
import type { AoiFeature, OperationalAlert } from "../api/types";
import AoiSelector from "../components/AoiSelector";
import ConfidencePanel from "../components/ConfidencePanel";
import ExplainabilityGallery from "../components/ExplainabilityGallery";
import LayerControls from "../components/LayerControls";
import TimelinePanel from "../components/TimelinePanel";
import { useExplainability } from "../hooks/useExplainability";
import MapView from "../maps/MapView";
import { centerFromAoi } from "../maps/geoUtils";
import type { LayerVisibility } from "../overlays/MapOverlays";
import StatusBadge from "../components/StatusBadge";

// Lazy-load the heavy CesiumGlobe to avoid blocking initial 2D load
const CesiumGlobe = lazy(() => import("../maps/CesiumGlobe"));

type ViewMode = "2d" | "3d";

interface DashboardPageProps {
  viewMode?: ViewMode;
  onModeChange?: (mode: ViewMode) => void;
}

export default function DashboardPage({ viewMode: propViewMode, onModeChange }: DashboardPageProps) {
  const [internalViewMode, setInternalViewMode] = useState<ViewMode>("3d");
  const viewMode = propViewMode ?? internalViewMode;
  const setViewMode = onModeChange ?? setInternalViewMode;

  const [aois, setAois] = useState<AoiFeature[]>([]);
  const [selectedAoiId, setSelectedAoiId] = useState<string | null>(null);
  const [layers, setLayers] = useState<LayerVisibility>({
    boundary: true,
    anomaly: true,
    osint: true,
  });
  const [alert, setAlert] = useState<OperationalAlert | null>(null);
  const [expStatus, setExpStatus] = useState<{ has_run: boolean; artifacts?: number }>({
    has_run: false,
  });

  const { manifest, overlays, loading, error, reload } = useExplainability(selectedAoiId);

  const selectedAoi = useMemo(
    () => aois.find((a) => a.properties.aoi_id === selectedAoiId) ?? null,
    [aois, selectedAoiId]
  );

  useEffect(() => {
    fetchAois()
      .then((fc) => {
        setAois(fc.features);
        if (fc.features.length > 0 && !selectedAoiId) {
          setSelectedAoiId(fc.features[0].properties.aoi_id);
        }
      })
      .catch(() => setAois([]));
  }, []);

  useEffect(() => {
    fetchExplainabilityStatus()
      .then((s) =>
        setExpStatus({
          has_run: s.has_run,
          artifacts: s.last_run?.artifacts_total,
        })
      )
      .catch(() => setExpStatus({ has_run: false }));
  }, [manifest]);

  useEffect(() => {
    if (!selectedAoiId) {
      setAlert(null);
      return;
    }
    fetchAlertsStatus()
      .then((s) => {
        const match = s.last_run?.alerts?.find((a) => a.aoi_id === selectedAoiId);
        setAlert(match ?? null);
      })
      .catch(() => setAlert(null));
  }, [selectedAoiId, manifest]);

  return (
    <div className={`dashboard ${viewMode === "3d" ? "dashboard-3d" : ""}`}>
      {/* ── Top toolbar with mode switcher (only displayed in 2D SAR mode) ── */}
      {viewMode === "2d" && (
        <div className="dashboard-toolbar">
          <div className="mode-switcher">
            <button
              id="mode-btn-2d"
              className="mode-btn active"
              onClick={() => setViewMode("2d")}
              title="2D SAR Anomaly Studio (Leaflet)"
            >
              🗺️ 2D SAR STUDIO
            </button>
            <button
              id="mode-btn-3d"
              className="mode-btn"
              onClick={() => setViewMode("3d")}
              title="3D Tactical Globe & Situational Cockpit (CesiumJS)"
            >
              🌐 3D TACTICAL COCKPIT
            </button>
          </div>

          <AoiSelector
            aois={aois}
            selectedId={selectedAoiId}
            onSelect={setSelectedAoiId}
            disabled={loading}
          />
          <LayerControls
            layers={layers}
            onChange={setLayers}
            hasBoundary={Boolean(overlays.boundary?.features.length)}
            hasAnomaly={Boolean(overlays.anomaly?.features.length)}
            hasOsint={Boolean(overlays.osint?.features.length)}
          />
          <div className="toolbar-status">
            <StatusBadge label={expStatus.has_run ? "explainability ready" : "no visuals"} ok={expStatus.has_run} />
            {loading && <span className="loading-hint">Loading…</span>}
            {error && (
              <span className="error-hint" title={error}>
                {error}
                <button type="button" className="link-btn" onClick={reload}>
                  Retry
                </button>
              </span>
            )}
          </div>
        </div>
      )}

      {/* ── Main content area ── */}
      {viewMode === "2d" ? (
        <div className="dashboard-main">
          <div className="map-pane">
            <MapView
              boundary={overlays.boundary}
              anomaly={overlays.anomaly}
              osint={overlays.osint}
              layers={layers}
              fallbackCenter={centerFromAoi(selectedAoi)}
            />
          </div>
          <aside className="analyst-panel">
            <ConfidencePanel
              breakdown={manifest?.confidence_breakdown ?? null}
              alert={alert}
              loading={loading}
            />
            <TimelinePanel events={manifest?.timeline ?? []} runId={manifest?.run_id} />
            {selectedAoiId && manifest && (
              <ExplainabilityGallery aoiId={selectedAoiId} artifacts={manifest.artifacts} />
            )}
          </aside>
        </div>
      ) : (
        <div
          className="map-pane"
          style={{
            position: "fixed",
            inset: 0,
            width: "100vw",
            height: "100vh",
            overflow: "hidden",
            zIndex: 10,
          }}
        >
          <Suspense
            fallback={
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  color: "var(--cyan)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.85rem",
                  letterSpacing: "0.1em",
                  textShadow: "0 0 12px var(--cyan-glow)",
                }}
              >
                ◈ INITIALISING 3D TACTICAL GLOBE…
              </div>
            }
          >
            <CesiumGlobe
              aois={aois}
              selectedAoiId={selectedAoiId}
              onSelectAoi={setSelectedAoiId}
              onSwitchTo2D={() => setViewMode("2d")}
            />
          </Suspense>
        </div>
      )}
    </div>
  );
}
