/**
 * TransitLayer.ts — Live Municipal Public Transit Vehicles (GTFS-RT Protobuf).
 *
 * Polls /api/live/transit/vehicles/mbta and /api/live/transit/vehicles/hsl.
 * Renders directional ground transit vehicles (trains, light rail, trams, buses)
 * with heading orientation, route badges, and speed telemetry.
 */

import * as Cesium from "cesium";

export interface TransitVehicle {
  id: string;
  label: string;
  latitude: number;
  longitude: number;
  bearing: number | null;
  speed_kmh: number | null;
  route_id: string | null;
  status: string;
  agency?: string;
}

const POLL_INTERVAL_MS = 20_000;
const AGENCIES = ["mbta", "hsl"];

function buildTransitCanvas(bearing: number | null, routeId?: string | null): HTMLCanvasElement {
  const size = 24;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;

  const hdg = bearing ?? 0;
  ctx.save();
  ctx.translate(size / 2, size / 2);
  ctx.rotate(Cesium.Math.toRadians(hdg));

  const isRail = routeId?.toLowerCase().includes("red") ||
                routeId?.toLowerCase().includes("green") ||
                routeId?.toLowerCase().includes("orange") ||
                routeId?.toLowerCase().includes("blue");

  const color = isRail ? "#ffdd00" : "#00f0ff";
  ctx.fillStyle = color;
  ctx.shadowColor = color;
  ctx.shadowBlur = 6;

  // Modern train / transit cab chevron
  ctx.beginPath();
  ctx.moveTo(0, -9);
  ctx.lineTo(5, 5);
  ctx.lineTo(3, 8);
  ctx.lineTo(-3, 8);
  ctx.lineTo(-5, 5);
  ctx.closePath();
  ctx.fill();

  ctx.restore();
  return canvas;
}

export class TransitLayer {
  private viewer: Cesium.Viewer;
  private billboards: Cesium.BillboardCollection;
  private labels: Cesium.LabelCollection;
  private vehicles: Map<string, TransitVehicle> = new Map();
  private visible = true;
  private pollTimer: number | null = null;
  private onCountUpdate?: (n: number) => void;
  private onVehicleClick?: (vehicle: TransitVehicle) => void;

  constructor(
    viewer: Cesium.Viewer,
    onCountUpdate?: (n: number) => void,
    onVehicleClick?: (vehicle: TransitVehicle) => void
  ) {
    this.viewer = viewer;
    this.onCountUpdate = onCountUpdate;
    this.onVehicleClick = onVehicleClick;

    this.billboards = viewer.scene.primitives.add(
      new Cesium.BillboardCollection({ scene: viewer.scene })
    );
    this.labels = viewer.scene.primitives.add(new Cesium.LabelCollection());

    this.fetchAllAgencies();
    this.pollTimer = window.setInterval(() => this.fetchAllAgencies(), POLL_INTERVAL_MS);

    viewer.screenSpaceEventHandler.setInputAction((click: { position: Cesium.Cartesian2 }) => {
      const picked = viewer.scene.pick(click.position);
      if (typeof picked?.id === "string" && picked.id.startsWith("transit:")) {
        const vId = picked.id.replace("transit:", "");
        const vehicle = this.vehicles.get(vId);
        if (vehicle && this.onVehicleClick) {
          this.onVehicleClick(vehicle);
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  private async fetchAllAgencies() {
    try {
      const results = await Promise.allSettled(
        AGENCIES.map((agency) =>
          fetch(`/api/live/transit/vehicles/${agency}`).then((r) => (r.ok ? r.json() : null))
        )
      );

      this.billboards.removeAll();
      this.labels.removeAll();
      this.vehicles.clear();

      for (const res of results) {
        if (res.status !== "fulfilled" || !res.value) continue;
        const data = res.value;
        const agencyName = data.agency || "Transit";
        const list: TransitVehicle[] = data.vehicles ?? [];

        for (const v of list) {
          if (v.latitude == null || v.longitude == null) continue;
          v.agency = agencyName;
          this.vehicles.set(v.id, v);

          const icon = buildTransitCanvas(v.bearing, v.route_id);
          const pos = Cesium.Cartesian3.fromDegrees(v.longitude, v.latitude, 10);

          this.billboards.add({
            position: pos,
            image: icon,
            id: `transit:${v.id}`,
            width: 20,
            height: 20,
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 300_000),
            show: this.visible,
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          });

          // Show label with route / vehicle ID
          const labelText = v.route_id ? `[${v.route_id}] ${v.label || v.id}` : v.label || v.id;
          this.labels.add({
            position: pos,
            text: labelText.slice(0, 16),
            font: "9px JetBrains Mono, monospace",
            fillColor: Cesium.Color.fromCssColorString("#00f0ff"),
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            pixelOffset: new Cesium.Cartesian2(0, -14),
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 150_000),
            disableDepthTestDistance: 500000,
            show: this.visible,
          });
        }
      }

      this.onCountUpdate?.(this.vehicles.size);
    } catch (_) {
      // Transit feed is non-fatal
    }
  }

  setVisible(visible: boolean) {
    this.visible = visible;
    this.billboards.show = visible;
    this.labels.show = visible;
  }

  destroy() {
    if (this.pollTimer !== null) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    this.viewer.scene.primitives.remove(this.billboards);
    this.viewer.scene.primitives.remove(this.labels);
  }
}
