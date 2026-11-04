/**
 * FirmsLayer.ts — NASA FIRMS Active Fire & Thermal Anomaly Detection Layer.
 *
 * Polls /api/live/firms.
 * Renders thermal hotspots with radiative power (FRP) scaled pulsation icons.
 */

import * as Cesium from "cesium";

export interface FirmsHotspot {
  id: string;
  latitude: number;
  longitude: number;
  brightness: number;
  frp: number;
  confidence: string;
  satellite: string;
  acq_date: string;
  acq_time: string;
}

const POLL_INTERVAL_MS = 60_000;

function buildFireCanvas(frp: number): HTMLCanvasElement {
  const size = Math.max(24, Math.min(48, Math.round(18 + (frp / 20))));
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;

  const cx = size / 2;
  const cy = size / 2;

  // Outer thermal bloom
  const grad = ctx.createRadialGradient(cx, cy, 2, cx, cy, size / 2 - 2);
  grad.addColorStop(0, "#ffffff");
  grad.addColorStop(0.3, "#ffcc00");
  grad.addColorStop(0.7, "#ff3b00");
  grad.addColorStop(1, "rgba(255, 59, 0, 0)");

  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.arc(cx, cy, size / 2 - 2, 0, Math.PI * 2);
  ctx.fill();

  // Central core
  ctx.fillStyle = "#ff1a00";
  ctx.beginPath();
  ctx.arc(cx, cy, 3, 0, Math.PI * 2);
  ctx.fill();

  return canvas;
}

export class FirmsLayer {
  private viewer: Cesium.Viewer;
  private collection: Cesium.BillboardCollection;
  private timer: number | null = null;
  private onCountUpdate?: (count: number) => void;
  private onSelect?: (hotspot: FirmsHotspot) => void;
  private isVisible: boolean = true;
  private itemMap: Map<string, FirmsHotspot> = new Map();

  constructor(
    viewer: Cesium.Viewer,
    onCountUpdate?: (count: number) => void,
    onSelect?: (hotspot: FirmsHotspot) => void
  ) {
    this.viewer = viewer;
    this.onCountUpdate = onCountUpdate;
    this.onSelect = onSelect;

    this.collection = new Cesium.BillboardCollection({
      scene: viewer.scene,
    });
    this.viewer.scene.primitives.add(this.collection);

    this.initPickHandler();
    this.poll();
    this.timer = window.setInterval(() => this.poll(), POLL_INTERVAL_MS);
  }

  private initPickHandler() {
    const handler = new Cesium.ScreenSpaceEventHandler(this.viewer.scene.canvas);
    handler.setInputAction((click: { position: Cesium.Cartesian2 }) => {
      if (!this.isVisible || !this.onSelect) return;
      const picked = this.viewer.scene.pick(click.position);
      if (picked && picked.id && typeof picked.id === "string" && picked.id.startsWith("firms-")) {
        const id = picked.id.replace("firms-", "");
        const spot = this.itemMap.get(id);
        if (spot) this.onSelect(spot);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  private async poll() {
    try {
      const res = await fetch("/api/live/firms");
      if (!res.ok) return;
      const data = await res.json();
      const hotspots: FirmsHotspot[] = data.hotspots || [];

      this.itemMap.clear();
      this.collection.removeAll();

      if (!this.isVisible) {
        if (this.onCountUpdate) this.onCountUpdate(hotspots.length);
        return;
      }

      for (const spot of hotspots) {
        this.itemMap.set(spot.id, spot);
        const pos = Cesium.Cartesian3.fromDegrees(spot.longitude, spot.latitude, 50);
        const canvas = buildFireCanvas(spot.frp || 50);

        this.collection.add({
          id: `firms-${spot.id}`,
          position: pos,
          image: canvas,
          scale: 1.0,
          horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
          verticalOrigin: Cesium.VerticalOrigin.CENTER,
        });
      }

      if (this.onCountUpdate) this.onCountUpdate(hotspots.length);
    } catch {
      // Soft-fail
    }
  }

  public setVisible(v: boolean) {
    this.isVisible = v;
    this.collection.show = v;
    if (v) this.poll();
  }

  public destroy() {
    if (this.timer) clearInterval(this.timer);
    if (!this.viewer.isDestroyed()) {
      this.viewer.scene.primitives.remove(this.collection);
    }
  }
}
