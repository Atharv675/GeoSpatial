/**
 * MilitaryLayer.ts — Dedicated Military Aircraft & Reconnaissance Tracks Layer.
 *
 * Polls /api/live/military.
 * Renders military assets (RC-135, FORTE Global Hawk, P-8 Poseidon, Fighters, Tankers)
 * with distinctive tactical diamond icons, flight vectors, and altitude tags.
 */

import * as Cesium from "cesium";

export interface MilitaryTrack {
  icao24: string;
  callsign?: string;
  origin_country?: string;
  latitude: number;
  longitude: number;
  baro_altitude?: number;
  velocity?: number;
  true_track?: number;
  category: string;
}

const POLL_INTERVAL_MS = 15_000;

function buildMilitaryCanvas(category: string, heading: number = 0): HTMLCanvasElement {
  const size = 36;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;

  const cx = size / 2;
  const cy = size / 2;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate((heading * Math.PI) / 180);

  // Tactical diamond
  const color = category === "reconnaissance" ? "#ff0055" : "#ff3366";
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.fillStyle = "rgba(255, 0, 85, 0.25)";

  ctx.beginPath();
  ctx.moveTo(0, -14);
  ctx.lineTo(12, 0);
  ctx.lineTo(0, 14);
  ctx.lineTo(-12, 0);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  // Heading pointer
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(-4, -14);
  ctx.lineTo(0, -18);
  ctx.lineTo(4, -14);
  ctx.closePath();
  ctx.fill();

  ctx.restore();
  return canvas;
}

export class MilitaryLayer {
  private viewer: Cesium.Viewer;
  private collection: Cesium.BillboardCollection;
  private timer: number | null = null;
  private onCountUpdate?: (count: number) => void;
  private onSelect?: (track: MilitaryTrack) => void;
  private isVisible: boolean = true;
  private trackMap: Map<string, MilitaryTrack> = new Map();

  constructor(
    viewer: Cesium.Viewer,
    onCountUpdate?: (count: number) => void,
    onSelect?: (track: MilitaryTrack) => void
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
      if (picked && picked.id && typeof picked.id === "string" && picked.id.startsWith("mil-")) {
        const icao = picked.id.replace("mil-", "");
        const track = this.trackMap.get(icao);
        if (track) this.onSelect(track);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  private async poll() {
    try {
      const res = await fetch("/api/live/military");
      if (!res.ok) return;
      const data = await res.json();
      const tracks: MilitaryTrack[] = data.tracks || [];

      this.trackMap.clear();
      this.collection.removeAll();

      if (!this.isVisible) {
        if (this.onCountUpdate) this.onCountUpdate(tracks.length);
        return;
      }

      for (const t of tracks) {
        if (t.latitude == null || t.longitude == null) continue;
        this.trackMap.set(t.icao24, t);

        const alt = t.baro_altitude || 10000;
        const pos = Cesium.Cartesian3.fromDegrees(t.longitude, t.latitude, alt);
        const canvas = buildMilitaryCanvas(t.category, t.true_track || 0);

        this.collection.add({
          id: `mil-${t.icao24}`,
          position: pos,
          image: canvas,
          scale: 1.0,
          horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
          verticalOrigin: Cesium.VerticalOrigin.CENTER,
        });
      }

      if (this.onCountUpdate) this.onCountUpdate(tracks.length);
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
