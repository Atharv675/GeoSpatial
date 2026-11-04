import { useEffect, useState } from "react";
import { fetchHealth, fetchReady, type ReadyResponse } from "./api/client";
import DashboardPage from "./pages/DashboardPage";

export default function App() {
  const [health, setHealth] = useState<string>("checking…");
  const [ready, setReady] = useState<ReadyResponse | null>(null);
  const [viewMode, setViewMode] = useState<"2d" | "3d">("3d");

  useEffect(() => {
    fetchHealth()
      .then((h) => setHealth(h.status))
      .catch(() => setHealth("unreachable"));
    fetchReady()
      .then(setReady)
      .catch(() => setReady(null));
  }, []);

  return (
    <div className={`app-layout ${viewMode === "3d" ? "mode-3d-fullscreen" : ""}`}>
      {viewMode === "2d" && (
        <aside className="sidebar">
          <h1>GeoSentinel</h1>
          <p className="tagline">Dual-mode geospatial intelligence &amp; OSINT fusion</p>
          <dl className="status-panel">
            <dt>API health</dt>
            <dd>{health}</dd>
            {ready && (
              <>
                <dt>Readiness</dt>
                <dd>{ready.status}</dd>
                <dt>Scope (AOIs max)</dt>
                <dd>{ready.scope?.max_aois ?? "—"}</dd>
                <dt>Time range (days)</dt>
                <dd>{ready.scope?.time_range_days ?? "—"}</dd>
              </>
            )}
          </dl>
          <p className="sidebar-note">
            <strong style={{ color: "var(--cyan)" }}>2D SAR STUDIO</strong> — Sentinel-1 SAR
            interferometry, Sentinel-2 optical indices, PostGIS AOIs, temporal raster
            differencing, OSINT fusion, explainability visuals.
            <br />
            <br />
            <strong style={{ color: "var(--green-radar)" }}>3D TACTICAL COCKPIT</strong> — Live
            ADS-B aircraft, AIS vessels, SGP4 orbital satellites, USGS seismic telemetry, GTFS-RT
            transit, NOAA radar WMS, public CCTV feeds. Keyless out-of-the-box.
          </p>
        </aside>
      )}
      <main className="main-content">
        <DashboardPage viewMode={viewMode} onModeChange={setViewMode} />
      </main>
    </div>
  );
}
