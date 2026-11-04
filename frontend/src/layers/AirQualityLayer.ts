/**
 * AirQualityLayer.ts — Global Environmental Air Quality (AQI) Sensors Layer.
 *
 * Polls /api/live/airquality.
 * Renders AQI stations colored by hazard levels (Green / Yellow / Orange / Red / Purple).
 */

import * as Cesium from "cesium";

export interface AqiStation {
  id: string;
  city: string;
  country: string;
  latitude: number;
  longitude: number;
  aqi: number;
  category: string;
  pm25: number;
  pm10: number;
}

const POLL_INTERVAL_MS = 60_000;

function aqiColor(aqi: number): string {
  if (aqi > 300) return "#7e0023"; // Hazardous (Maroon)
  if (aqi > 200) return "#8f3f97"; // Very Unhealthy (Purple)
  if (aqi > 150) return "#ff0000"; // Unhealthy (Red)
  if (aqi > 100) return "#ff7e00"; // Sensitive (Orange)
  if (aqi > 50) return "#ffff00";  // Moderate (Yellow)
  return "#00e400"; // Good (Green)
}

function buildAqiCanvas(aqi: number): HTMLCanvasElement {
  const size = 32;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const cx = size / 2;
  const cy = size / 2;
  const color = aqiColor(aqi);

  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(cx, cy, 10, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 1.5;
  ctx.stroke();

  return canvas;
}

export class AirQualityLayer {
  private viewer: Cesium.Viewer;
  private collection: Cesium.BillboardCollection;
  private timer: number | null = null;
  private onCountUpdate?: (count: number) => void;
  private onSelect?: (station: AqiStation) => void;
  private isVisible: boolean = true;
  private itemMap: Map<string, AqiStation> = new Map();

  constructor(
    viewer: Cesium.Viewer,
    onCountUpdate?: (count: number) => void,
    onSelect?: (station: AqiStation) => void
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
      if (picked && picked.id && typeof picked.id === "string" && picked.id.startsWith("aqi-")) {
        const id = picked.id.replace("aqi-", "");
        const station = this.itemMap.get(id);
        if (station) this.onSelect(station);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  private async poll() {
    try {
      const res = await fetch("/api/live/airquality");
      if (!res.ok) return;
      const data = await res.json();
      const stations: AqiStation[] = data.stations || [];

      this.itemMap.clear();
      this.collection.removeAll();

      if (!this.isVisible) {
        if (this.onCountUpdate) this.onCountUpdate(stations.length);
        return;
      }

      for (const st of stations) {
        this.itemMap.set(st.id, st);
        const pos = Cesium.Cartesian3.fromDegrees(st.longitude, st.latitude, 20);
        const canvas = buildAqiCanvas(st.aqi);

        this.collection.add({
          id: `aqi-${st.id}`,
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
