/**
 * PerimeterLayer.ts — Tactical Geofences & Air Defense Identification Zones (ADIZ).
 *
 * Polls /api/live/perimeters.
 * Renders glowing polygon boundaries and airspace corridors.
 */

import * as Cesium from "cesium";

export interface TacticalPerimeter {
  id: string;
  name: string;
  type: string;
  classification: string;
  coordinates: number[][]; // [lon, lat]
}

const POLL_INTERVAL_MS = 300_000;

export class PerimeterLayer {
  private viewer: Cesium.Viewer;
  private entities: Cesium.Entity[] = [];
  private timer: number | null = null;
  private onCountUpdate?: (count: number) => void;
  private onSelect?: (perim: TacticalPerimeter) => void;
  private isVisible: boolean = true;
  private itemMap: Map<string, TacticalPerimeter> = new Map();

  constructor(
    viewer: Cesium.Viewer,
    onCountUpdate?: (count: number) => void,
    onSelect?: (perim: TacticalPerimeter) => void
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
      if (picked && picked.id && typeof picked.id === "object" && picked.id.id && typeof picked.id.id === "string" && picked.id.id.startsWith("perim-")) {
        const id = picked.id.id.replace("perim-", "");
        const perim = this.itemMap.get(id);
        if (perim) this.onSelect(perim);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  private async poll() {
    try {
      const res = await fetch("/api/live/perimeters");
      if (!res.ok) return;
      const data = await res.json();
      const perims: TacticalPerimeter[] = data.perimeters || [];

      this.itemMap.clear();
      this.clearEntities();

      if (!this.isVisible) {
        if (this.onCountUpdate) this.onCountUpdate(perims.length);
        return;
      }

      for (const p of perims) {
        this.itemMap.set(p.id, p);
        const hierarchy = p.coordinates.map((coord) =>
          Cesium.Cartesian3.fromDegrees(coord[0], coord[1], 100)
        );

        const ent = this.viewer.entities.add({
          id: `perim-${p.id}`,
          polygon: {
            hierarchy: new Cesium.PolygonHierarchy(hierarchy),
            material: Cesium.Color.fromCssColorString("#ff0055").withAlpha(0.12),
            outline: true,
            outlineColor: Cesium.Color.fromCssColorString("#ff0055").withAlpha(0.8),
            outlineWidth: 2,
          },
        });
        this.entities.push(ent);
      }

      if (this.onCountUpdate) this.onCountUpdate(perims.length);
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
