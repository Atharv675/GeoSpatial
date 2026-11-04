/**
 * CycloneLayer.ts — NOAA NHC Tropical Cyclones & Hurricanes Layer.
 *
 * Polls /api/live/weather/cyclones.
 * Renders storm center vortex billboards and predicted track trajectories.
 */

import * as Cesium from "cesium";

export interface CycloneRecord {
  id: string;
  name: string;
  classification: string;
  intensity_mph: number;
  pressure_mb: number;
  latitude: number;
  longitude: number;
  movement_dir: string;
  movement_speed_mph: number;
  advisory_time: string;
}

const POLL_INTERVAL_MS = 120_000;

function buildCycloneCanvas(intensity: number): HTMLCanvasElement {
  const size = 44;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const cx = size / 2;
  const cy = size / 2;

  // Swirl spiral arms
  ctx.strokeStyle = intensity >= 111 ? "#ff0055" : intensity >= 74 ? "#ff8800" : "#00e5ff";
  ctx.lineWidth = 2.5;

  ctx.beginPath();
  for (let i = 0; i < 40; i++) {
    const angle = 0.25 * i;
    const r = 2 + 0.45 * i;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();

  // Eye
  ctx.fillStyle = "#ffffff";
  ctx.beginPath();
  ctx.arc(cx, cy, 3, 0, Math.PI * 2);
  ctx.fill();

  return canvas;
}

export class CycloneLayer {
  private viewer: Cesium.Viewer;
  private collection: Cesium.BillboardCollection;
  private timer: number | null = null;
  private onCountUpdate?: (count: number) => void;
  private onSelect?: (cyclone: CycloneRecord) => void;
  private isVisible: boolean = true;
  private itemMap: Map<string, CycloneRecord> = new Map();

  constructor(
    viewer: Cesium.Viewer,
    onCountUpdate?: (count: number) => void,
    onSelect?: (cyclone: CycloneRecord) => void
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
      if (picked && picked.id && typeof picked.id === "string" && picked.id.startsWith("cyclone-")) {
        const id = picked.id.replace("cyclone-", "");
        const storm = this.itemMap.get(id);
        if (storm) this.onSelect(storm);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  private async poll() {
    try {
      const res = await fetch("/api/live/weather/cyclones");
      if (!res.ok) return;
      const data = await res.json();
      const cyclones: CycloneRecord[] = data.cyclones || [];

      this.itemMap.clear();
      this.collection.removeAll();

      if (!this.isVisible) {
        if (this.onCountUpdate) this.onCountUpdate(cyclones.length);
        return;
      }

      for (const c of cyclones) {
        this.itemMap.set(c.id, c);
        const pos = Cesium.Cartesian3.fromDegrees(c.longitude, c.latitude, 500);
        const canvas = buildCycloneCanvas(c.intensity_mph || 75);

        this.collection.add({
          id: `cyclone-${c.id}`,
          position: pos,
          image: canvas,
          scale: 1.0,
          horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
          verticalOrigin: Cesium.VerticalOrigin.CENTER,
        });
      }

      if (this.onCountUpdate) this.onCountUpdate(cyclones.length);
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
