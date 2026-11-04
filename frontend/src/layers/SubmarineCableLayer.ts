/**
 * SubmarineCableLayer.ts — Global Undersea Fiber Optic Telecommunication Cables Layer.
 *
 * Polls /api/live/cables.
 * Renders glowing polyline paths traversing oceanic basins and international waters.
 */

import * as Cesium from "cesium";

export interface SubmarineCable {
  id: string;
  name: string;
  status: string;
  capacity: string;
  coordinates: number[][]; // [lon, lat]
}

const POLL_INTERVAL_MS = 300_000;

export class SubmarineCableLayer {
  private viewer: Cesium.Viewer;
  private polylines: Cesium.PolylineCollection;
  private timer: number | null = null;
  private onCountUpdate?: (count: number) => void;
  private onSelect?: (cable: SubmarineCable) => void;
  private isVisible: boolean = true;
  private itemMap: Map<string, SubmarineCable> = new Map();

  constructor(
    viewer: Cesium.Viewer,
    onCountUpdate?: (count: number) => void,
    onSelect?: (cable: SubmarineCable) => void
  ) {
    this.viewer = viewer;
    this.onCountUpdate = onCountUpdate;
    this.onSelect = onSelect;

    this.polylines = new Cesium.PolylineCollection();
    this.viewer.scene.primitives.add(this.polylines);

    this.initPickHandler();
    this.poll();
    this.timer = window.setInterval(() => this.poll(), POLL_INTERVAL_MS);
  }

  private initPickHandler() {
    const handler = new Cesium.ScreenSpaceEventHandler(this.viewer.scene.canvas);
    handler.setInputAction((click: { position: Cesium.Cartesian2 }) => {
      if (!this.isVisible || !this.onSelect) return;
      const picked = this.viewer.scene.pick(click.position);
      if (picked && picked.id && typeof picked.id === "string" && picked.id.startsWith("cable-")) {
        const id = picked.id.replace("cable-", "");
        const cable = this.itemMap.get(id);
        if (cable) this.onSelect(cable);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  private async poll() {
    try {
      const res = await fetch("/api/live/cables");
      if (!res.ok) return;
      const data = await res.json();
      const cables: SubmarineCable[] = data.cables || [];

      this.itemMap.clear();
      this.polylines.removeAll();

      if (!this.isVisible) {
        if (this.onCountUpdate) this.onCountUpdate(cables.length);
        return;
      }

      for (const cable of cables) {
        this.itemMap.set(cable.id, cable);
        const positions = cable.coordinates.map((coord) =>
          Cesium.Cartesian3.fromDegrees(coord[0], coord[1], 100)
        );

        this.polylines.add({
          id: `cable-${cable.id}`,
          positions: positions,
          width: 3.0,
          material: Cesium.Material.fromType("Color", {
            color: Cesium.Color.fromCssColorString("#00e5ff").withAlpha(0.75),
          }),
        });
      }

      if (this.onCountUpdate) this.onCountUpdate(cables.length);
    } catch {
      // Soft-fail
    }
  }

  public setVisible(v: boolean) {
    this.isVisible = v;
    this.polylines.show = v;
    if (v) this.poll();
  }

  public destroy() {
    if (this.timer) clearInterval(this.timer);
    if (!this.viewer.isDestroyed()) {
      this.viewer.scene.primitives.remove(this.polylines);
    }
  }
}
