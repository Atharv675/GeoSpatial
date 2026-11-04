/**
 * EarthquakeLayer.ts — USGS Real-Time Global Seismic Telemetry Layer.
 *
 * Polls /api/live/earthquakes.
 * Renders seismic events scaled by magnitude with depth markers and impact rings.
 * Color coded:
 *   - Green: M < 4.0 (Minor)
 *   - Amber: 4.0 <= M < 6.0 (Moderate to Strong)
 *   - Crimson / Neon Red: M >= 6.0 (Major / Destructive)
 */

import * as Cesium from "cesium";

export interface EarthquakeRecord {
  id: string;
  magnitude: number;
  place: string;
  time: number;
  latitude: number;
  longitude: number;
  depth_km: number;
  tsunami: number;
  alert: string | null;
}

const POLL_INTERVAL_MS = 60_000;

function quakeColor(mag: number): string {
  if (mag >= 6.0) return "#ff0055"; // Destructive
  if (mag >= 4.5) return "#ff9900"; // Moderate / Strong
  if (mag >= 3.0) return "#ffd700"; // Light
  return "#00ff9d"; // Minor
}

function buildQuakeCanvas(mag: number): HTMLCanvasElement {
  const size = Math.max(20, Math.min(48, Math.round(14 + mag * 5)));
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const color = quakeColor(mag);

  const center = size / 2;
  const radius = size / 2 - 3;

  // Outer pulse wave ring
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(center, center, radius, 0, Math.PI * 2);
  ctx.stroke();

  // Concentric ring
  ctx.strokeStyle = color;
  ctx.lineWidth = 1;
  ctx.setLineDash([2, 2]);
  ctx.beginPath();
  ctx.arc(center, center, radius * 0.65, 0, Math.PI * 2);
  ctx.stroke();
  ctx.setLineDash([]);

  // Inner solid core
  ctx.fillStyle = color;
  ctx.shadowColor = color;
  ctx.shadowBlur = 8;
  ctx.beginPath();
  ctx.arc(center, center, Math.max(3, radius * 0.35), 0, Math.PI * 2);
  ctx.fill();

  return canvas;
}

export class EarthquakeLayer {
  private viewer: Cesium.Viewer;
  private billboards: Cesium.BillboardCollection;
  private labels: Cesium.LabelCollection;
  private quakes: EarthquakeRecord[] = [];
  private visible = true;
  private pollTimer: number | null = null;
  private onCountUpdate?: (n: number) => void;
  private onQuakeClick?: (quake: EarthquakeRecord) => void;

  constructor(
    viewer: Cesium.Viewer,
    onCountUpdate?: (n: number) => void,
    onQuakeClick?: (quake: EarthquakeRecord) => void
  ) {
    this.viewer = viewer;
    this.onCountUpdate = onCountUpdate;
    this.onQuakeClick = onQuakeClick;

    this.billboards = viewer.scene.primitives.add(
      new Cesium.BillboardCollection({ scene: viewer.scene })
    );
    this.labels = viewer.scene.primitives.add(new Cesium.LabelCollection());

    this.fetchQuakes();
    this.pollTimer = window.setInterval(() => this.fetchQuakes(), POLL_INTERVAL_MS);

    viewer.screenSpaceEventHandler.setInputAction((click: { position: Cesium.Cartesian2 }) => {
      const picked = viewer.scene.pick(click.position);
      if (typeof picked?.id === "string" && picked.id.startsWith("quake:")) {
        const qId = picked.id.replace("quake:", "");
        const quake = this.quakes.find((q) => q.id === qId);
        if (quake && this.onQuakeClick) {
          this.onQuakeClick(quake);
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  private async fetchQuakes() {
    try {
      const resp = await fetch("/api/live/earthquakes");
      if (!resp.ok) return;
      const data = await resp.json();
      const items: EarthquakeRecord[] = data.earthquakes ?? [];
      this.quakes = items;

      this.billboards.removeAll();
      this.labels.removeAll();

      for (const q of items) {
        if (q.latitude == null || q.longitude == null) continue;
        const mag = q.magnitude || 2.0;
        const icon = buildQuakeCanvas(mag);
        const pos = Cesium.Cartesian3.fromDegrees(q.longitude, q.latitude, 0);

        this.billboards.add({
          position: pos,
          image: icon,
          id: `quake:${q.id}`,
          scaleByDistance: new Cesium.NearFarScalar(1.0e6, 1.0, 1.5e7, 0.45),
          show: this.visible,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        });

        // Label for significant quakes (M >= 4.0) only when zoomed in
        if (mag >= 4.0) {
          this.labels.add({
            position: pos,
            text: `M${mag.toFixed(1)} ${q.place ? q.place.slice(0, 24) : ""}`,
            font: "10px JetBrains Mono, monospace",
            fillColor: Cesium.Color.fromCssColorString(quakeColor(mag)),
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            pixelOffset: new Cesium.Cartesian2(0, -18),
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 3_000_000),
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
            show: this.visible,
          });
        }
      }

      this.onCountUpdate?.(items.length);
    } catch (_) {
      // Seismic telemetry is non-fatal
    }
  }

  setVisible(visible: boolean) {
    this.visible = visible;
    this.billboards.show = visible;
    this.labels.show = visible;
  }

  destroy() {
    if (this.pollTimer !== null) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    this.viewer.scene.primitives.remove(this.billboards);
    this.viewer.scene.primitives.remove(this.labels);
  }
}
