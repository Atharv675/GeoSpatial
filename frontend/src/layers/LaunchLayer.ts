/**
 * LaunchLayer.ts — Space Missions & Rocket Launches Layer.
 *
 * Polls /api/live/satellites/launches.
 * Renders spaceport launchpads, active countdowns, and launch vehicles.
 */

import * as Cesium from "cesium";

export interface SpaceLaunch {
  id: string;
  name: string;
  status: string;
  net: string;
  pad: {
    name: string;
    latitude: number;
    longitude: number;
    location: string;
  };
  mission?: {
    name: string;
    description: string;
    orbit: string;
  };
  lsp_name?: string;
}

const POLL_INTERVAL_MS = 120_000;

function buildRocketCanvas(): HTMLCanvasElement {
  const size = 36;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const cx = size / 2;
  const cy = size / 2;

  // Outer rocket booster circle
  ctx.strokeStyle = "#b45eff";
  ctx.lineWidth = 2;
  ctx.fillStyle = "rgba(180, 94, 255, 0.2)";
  ctx.beginPath();
  ctx.arc(cx, cy, 14, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();

  // Upward rocket glyph
  ctx.fillStyle = "#ffffff";
  ctx.beginPath();
  ctx.moveTo(cx, cy - 10);
  ctx.lineTo(cx + 6, cy + 6);
  ctx.lineTo(cx, cy + 3);
  ctx.lineTo(cx - 6, cy + 6);
  ctx.closePath();
  ctx.fill();

  return canvas;
}

export class LaunchLayer {
  private viewer: Cesium.Viewer;
  private collection: Cesium.BillboardCollection;
  private timer: number | null = null;
  private onCountUpdate?: (count: number) => void;
  private onSelect?: (launch: SpaceLaunch) => void;
  private isVisible: boolean = true;
  private itemMap: Map<string, SpaceLaunch> = new Map();

  constructor(
    viewer: Cesium.Viewer,
    onCountUpdate?: (count: number) => void,
    onSelect?: (launch: SpaceLaunch) => void
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
      if (picked && picked.id && typeof picked.id === "string" && picked.id.startsWith("launch-")) {
        const id = picked.id.replace("launch-", "");
        const l = this.itemMap.get(id);
        if (l) this.onSelect(l);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  private async poll() {
    try {
      const res = await fetch("/api/live/satellites/launches");
      if (!res.ok) return;
      const data = await res.json();
      const launches: SpaceLaunch[] = data.launches || [];

      this.itemMap.clear();
      this.collection.removeAll();

      if (!this.isVisible) {
        if (this.onCountUpdate) this.onCountUpdate(launches.length);
        return;
      }

      for (const l of launches) {
        if (!l.pad || l.pad.latitude == null || l.pad.longitude == null) continue;
        this.itemMap.set(l.id, l);
        const pos = Cesium.Cartesian3.fromDegrees(l.pad.longitude, l.pad.latitude, 100);
        const canvas = buildRocketCanvas();

        this.collection.add({
          id: `launch-${l.id}`,
          position: pos,
          image: canvas,
          scale: 1.0,
          horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
          verticalOrigin: Cesium.VerticalOrigin.CENTER,
        });
      }

      if (this.onCountUpdate) this.onCountUpdate(launches.length);
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
