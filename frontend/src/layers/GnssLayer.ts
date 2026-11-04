/**
 * GnssLayer.ts — GNSS / GPS Jamming & Electronic Warfare Interference Layer.
 *
 * Polls /api/live/gnss.
 * Renders interference perimeter domes and alert radials.
 */

import * as Cesium from "cesium";

export interface GnssZone {
  id: string;
  name: string;
  severity: string;
  radius_km: number;
  center: number[]; // [lon, lat]
  type: string;
  reported_anomalies: number;
}

const POLL_INTERVAL_MS = 60_000;

export class GnssLayer {
  private viewer: Cesium.Viewer;
  private entities: Cesium.Entity[] = [];
  private timer: number | null = null;
  private onCountUpdate?: (count: number) => void;
  private onSelect?: (zone: GnssZone) => void;
  private isVisible: boolean = true;
  private itemMap: Map<string, GnssZone> = new Map();

  constructor(
    viewer: Cesium.Viewer,
    onCountUpdate?: (count: number) => void,
    onSelect?: (zone: GnssZone) => void
  ) {
    this.viewer = viewer;
    this.onCountUpdate = onCountUpdate;
    this.onSelect = onSelect;

    this.initPickHandler();
    this.poll();
    this.timer = window.setInterval(() => this.poll(), POLL_INTERVAL_MS);
  }

  private initPickHandler() {
    const handler = new Cesium.ScreenSpaceEventHandler(this.viewer.scene.canvas);
    handler.setInputAction((click: { position: Cesium.Cartesian2 }) => {
      if (!this.isVisible || !this.onSelect) return;
      const picked = this.viewer.scene.pick(click.position);
      if (picked && picked.id && typeof picked.id === "object" && picked.id.id && typeof picked.id.id === "string" && picked.id.id.startsWith("gnss-")) {
        const id = picked.id.id.replace("gnss-", "");
        const zone = this.itemMap.get(id);
        if (zone) this.onSelect(zone);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  private async poll() {
    try {
      const res = await fetch("/api/live/gnss");
      if (!res.ok) return;
      const data = await res.json();
      const zones: GnssZone[] = data.zones || [];

      this.itemMap.clear();
      this.clearEntities();

      if (!this.isVisible) {
        if (this.onCountUpdate) this.onCountUpdate(zones.length);
        return;
      }

      for (const z of zones) {
        this.itemMap.set(z.id, z);
        const color =
          z.severity === "CRITICAL"
            ? Cesium.Color.fromCssColorString("#ff0055").withAlpha(0.2)
            : Cesium.Color.fromCssColorString("#ffaa00").withAlpha(0.18);

        const outlineColor =
          z.severity === "CRITICAL"
            ? Cesium.Color.fromCssColorString("#ff0055")
            : Cesium.Color.fromCssColorString("#ffaa00");

        const ent = this.viewer.entities.add({
          id: `gnss-${z.id}`,
          position: Cesium.Cartesian3.fromDegrees(z.center[0], z.center[1]),
          ellipse: {
            semiMinorAxis: z.radius_km * 1000,
            semiMajorAxis: z.radius_km * 1000,
            material: color,
            outline: true,
            outlineColor: outlineColor,
            outlineWidth: 2,
            height: 50,
          },
        });
        this.entities.push(ent);
      }

      if (this.onCountUpdate) this.onCountUpdate(zones.length);
    } catch {
      // Soft-fail
    }
  }

  private clearEntities() {
    for (const ent of this.entities) {
      this.viewer.entities.remove(ent);
    }
    this.entities = [];
  }

  public setVisible(v: boolean) {
    this.isVisible = v;
    for (const ent of this.entities) {
      ent.show = v;
    }
    if (v) this.poll();
  }

  public destroy() {
    if (this.timer) clearInterval(this.timer);
    this.clearEntities();
  }
}
