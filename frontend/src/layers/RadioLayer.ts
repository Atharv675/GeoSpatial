/**
 * RadioLayer.ts — WebSDR & VHF/HF ATC Airband Radio Monitoring Stations Layer.
 *
 * Polls /api/live/radio.
 * Renders radio towers and frequency transmitters with audio wave indicators.
 */

import * as Cesium from "cesium";

export interface RadioStation {
  id: string;
  name: string;
  frequency: string;
  type: string;
  latitude: number;
  longitude: number;
  status: string;
}

const POLL_INTERVAL_MS = 120_000;

function buildRadioCanvas(): HTMLCanvasElement {
  const size = 32;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const cx = size / 2;
  const cy = size / 2;

  // Radio antenna tower
  ctx.strokeStyle = "#00ff9d";
  ctx.lineWidth = 2;

  // Tower mast
  ctx.beginPath();
  ctx.moveTo(cx, cy - 10);
  ctx.lineTo(cx, cy + 10);
  ctx.lineTo(cx - 6, cy + 12);
  ctx.moveTo(cx, cy + 10);
  ctx.lineTo(cx + 6, cy + 12);
  ctx.stroke();

  // Radio wave arcs
  ctx.beginPath();
  ctx.arc(cx, cy - 10, 5, -Math.PI * 0.75, -Math.PI * 0.25);
  ctx.arc(cx, cy - 10, 9, -Math.PI * 0.75, -Math.PI * 0.25);
  ctx.stroke();

  return canvas;
}

export class RadioLayer {
  private viewer: Cesium.Viewer;
  private collection: Cesium.BillboardCollection;
  private timer: number | null = null;
  private onCountUpdate?: (count: number) => void;
  private onSelect?: (st: RadioStation) => void;
  private isVisible: boolean = true;
  private itemMap: Map<string, RadioStation> = new Map();

  constructor(
    viewer: Cesium.Viewer,
    onCountUpdate?: (count: number) => void,
    onSelect?: (st: RadioStation) => void
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
      if (picked && picked.id && typeof picked.id === "string" && picked.id.startsWith("radio-")) {
        const id = picked.id.replace("radio-", "");
        const st = this.itemMap.get(id);
        if (st) this.onSelect(st);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  private async poll() {
    try {
      const res = await fetch("/api/live/radio");
      if (!res.ok) return;
      const data = await res.json();
      const stations: RadioStation[] = data.stations || [];

      this.itemMap.clear();
      this.collection.removeAll();

      if (!this.isVisible) {
        if (this.onCountUpdate) this.onCountUpdate(stations.length);
        return;
      }

      for (const st of stations) {
        this.itemMap.set(st.id, st);
        const pos = Cesium.Cartesian3.fromDegrees(st.longitude, st.latitude, 30);
        const canvas = buildRadioCanvas();

        this.collection.add({
          id: `radio-${st.id}`,
          position: pos,
          image: canvas,
          scale: 1.0,
          horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
          verticalOrigin: Cesium.VerticalOrigin.CENTER,
        });
      }

      if (this.onCountUpdate) this.onCountUpdate(stations.length);
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
