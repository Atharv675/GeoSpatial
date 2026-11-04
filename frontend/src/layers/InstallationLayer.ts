/**
 * InstallationLayer.ts — Strategic Military Installations & Defense Sites Layer.
 *
 * Polls /api/live/installations.
 * Renders strategic bases, naval stations, and airfields with tactical base icons.
 */

import * as Cesium from "cesium";

export interface DefenseInstallation {
  id: string;
  name: string;
  country: string;
  type: string;
  latitude: number;
  longitude: number;
  status: string;
  elevation: number;
}

const POLL_INTERVAL_MS = 300_000;

function buildInstallationCanvas(): HTMLCanvasElement {
  const size = 32;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const cx = size / 2;
  const cy = size / 2;

  // Tactical base fortress hexagon
  ctx.strokeStyle = "#ffb700";
  ctx.lineWidth = 2;
  ctx.fillStyle = "rgba(255, 183, 0, 0.25)";

  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const angle = (i * 60 * Math.PI) / 180;
    const x = cx + 12 * Math.cos(angle);
    const y = cy + 12 * Math.sin(angle);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  // Internal star / shield dot
  ctx.fillStyle = "#ffffff";
  ctx.beginPath();
  ctx.arc(cx, cy, 3, 0, Math.PI * 2);
  ctx.fill();

  return canvas;
}

export class InstallationLayer {
  private viewer: Cesium.Viewer;
  private collection: Cesium.BillboardCollection;
  private timer: number | null = null;
  private onCountUpdate?: (count: number) => void;
  private onSelect?: (inst: DefenseInstallation) => void;
  private isVisible: boolean = true;
  private itemMap: Map<string, DefenseInstallation> = new Map();

  constructor(
    viewer: Cesium.Viewer,
    onCountUpdate?: (count: number) => void,
    onSelect?: (inst: DefenseInstallation) => void
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
      if (picked && picked.id && typeof picked.id === "string" && picked.id.startsWith("inst-")) {
        const id = picked.id.replace("inst-", "");
        const inst = this.itemMap.get(id);
        if (inst) this.onSelect(inst);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  private async poll() {
    try {
      const res = await fetch("/api/live/installations");
      if (!res.ok) return;
      const data = await res.json();
      const installations: DefenseInstallation[] = data.installations || [];

      this.itemMap.clear();
      this.collection.removeAll();

      if (!this.isVisible) {
        if (this.onCountUpdate) this.onCountUpdate(installations.length);
        return;
      }

      for (const inst of installations) {
        this.itemMap.set(inst.id, inst);
        const pos = Cesium.Cartesian3.fromDegrees(inst.longitude, inst.latitude, inst.elevation || 10);
        const canvas = buildInstallationCanvas();

        this.collection.add({
          id: `inst-${inst.id}`,
          position: pos,
          image: canvas,
          scale: 1.0,
          horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
          verticalOrigin: Cesium.VerticalOrigin.CENTER,
        });
      }

      if (this.onCountUpdate) this.onCountUpdate(installations.length);
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
