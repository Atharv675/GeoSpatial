/**
 * VesselLayer.ts — Live AIS vessel rendering via the backend WebSocket relay.
 *
 * Connects to ws://localhost:port/api/live/vessels/ws.
 * Renders moving ship markers with SOG, heading and MMSI tags.
 */

import * as Cesium from "cesium";

interface VesselRecord {
  mmsi: number;
  name?: string;
  type?: string;
  latitude: number;
  longitude: number;
  sog?: number;
  heading?: number;
  cog?: number;
  timestamp?: number;
}

const VESSEL_COLOR_CARGO    = Cesium.Color.fromCssColorString("#00e5ff");
const VESSEL_COLOR_TANKER   = Cesium.Color.fromCssColorString("#ffb700");
const VESSEL_COLOR_NAVAL    = Cesium.Color.fromCssColorString("#ff3b5c");
const VESSEL_COLOR_PILOT    = Cesium.Color.fromCssColorString("#00ff9d");
const VESSEL_COLOR_DEFAULT  = Cesium.Color.fromCssColorString("#8ea8c8");

function vesselColor(type?: string): Cesium.Color {
  if (!type) return VESSEL_COLOR_DEFAULT;
  const t = type.toLowerCase();
  if (t.includes("tanker")) return VESSEL_COLOR_TANKER;
  if (t.includes("naval") || t.includes("military") || t.includes("hospital")) return VESSEL_COLOR_NAVAL;
  if (t.includes("pilot")) return VESSEL_COLOR_PILOT;
  if (t.includes("cargo") || t.includes("container")) return VESSEL_COLOR_CARGO;
  return VESSEL_COLOR_DEFAULT;
}

function buildVesselCanvas(heading: number, type?: string): HTMLCanvasElement {
  const size = 24;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const color = vesselColor(type);
  const colorHex = `rgba(${Math.round(color.red * 255)},${Math.round(color.green * 255)},${Math.round(color.blue * 255)},1)`;

  ctx.save();
  ctx.translate(size / 2, size / 2);
  ctx.rotate(Cesium.Math.toRadians(heading));
  ctx.fillStyle = colorHex;
  ctx.shadowColor = colorHex;
  ctx.shadowBlur = 6;

  // Ship silhouette (pointing up = north = 0°)
  ctx.beginPath();
  ctx.moveTo(0, -9);  // bow
  ctx.lineTo(4, 4);
  ctx.lineTo(2, 8);
  ctx.lineTo(-2, 8);
  ctx.lineTo(-4, 4);
  ctx.closePath();
  ctx.fill();
  ctx.restore();

  return canvas;
}

export class VesselLayer {
  private viewer: Cesium.Viewer;
  private billboards: Cesium.BillboardCollection;
  private labels: Cesium.LabelCollection;
  private vesselMap: Map<number, { bb: Cesium.Billboard; label: Cesium.Label }> = new Map();
  private ws: WebSocket | null = null;
  private visible = true;
  private onCountUpdate: (n: number) => void;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(viewer: Cesium.Viewer, onCountUpdate: (n: number) => void) {
    this.viewer = viewer;
    this.onCountUpdate = onCountUpdate;
    this.billboards = viewer.scene.primitives.add(new Cesium.BillboardCollection({ scene: viewer.scene }));
    this.labels     = viewer.scene.primitives.add(new Cesium.LabelCollection());
    this.fetchSnapshot();
    this.connect();
  }

  private async fetchSnapshot() {
    try {
      const resp = await fetch("/api/live/vessels/snapshot");
      if (resp.ok) {
        const data = await resp.json();
        const vessels: VesselRecord[] = data.vessels ?? [];
        for (const v of vessels) this.updateVessel(v);
        this.onCountUpdate(this.vesselMap.size);
      }
    } catch (_) {}
  }

  private connect() {
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProtocol}//${window.location.host}/api/live/vessels/ws`;
    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.onmessage = (evt) => this.handleMessage(evt.data as string);
      this.ws.onclose = () => {
        // Reconnect after 5 seconds
        this.reconnectTimer = setTimeout(() => this.connect(), 5000);
      };
      this.ws.onerror = () => this.ws?.close();
    } catch (_) {}
  }

  private handleMessage(raw: string) {
    try {
      const msg = JSON.parse(raw);
      const vessels: VesselRecord[] = msg.vessels ?? (msg.vessel ? [msg.vessel] : []);
      for (const v of vessels) this.updateVessel(v);
      this.onCountUpdate(this.vesselMap.size);
    } catch (_) {}
  }

  private updateVessel(v: VesselRecord) {
    const heading = v.heading ?? v.cog ?? 0;
    const pos = Cesium.Cartesian3.fromDegrees(v.longitude, v.latitude, 10);
    const canvas = buildVesselCanvas(heading, v.type);
    const imageUrl = canvas.toDataURL();
    const label  = `${v.name?.trim() || String(v.mmsi)} ${v.sog != null ? `|${v.sog.toFixed(1)}kt` : ""}`;

    if (this.vesselMap.has(v.mmsi)) {
      const entry = this.vesselMap.get(v.mmsi)!;
      entry.bb.position = pos;
      entry.bb.image = imageUrl;
      entry.label.position = pos;
      entry.label.text = label;
    } else {
      const bb = this.billboards.add({
        position: pos,
        image: imageUrl,
        id: `vessel:${v.mmsi}`,
        width: 20,
        height: 20,
        scaleByDistance: new Cesium.NearFarScalar(1.0e6, 1.0, 1.2e7, 0.4),
        show: this.visible,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      });

      const lbl = this.labels.add({
        position: pos,
        text: label,
        font: "9px JetBrains Mono, monospace",
        fillColor: vesselColor(v.type),
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new Cesium.Cartesian2(0, -18),
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 1_800_000),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        show: this.visible,
      });

      this.vesselMap.set(v.mmsi, { bb, label: lbl });
    }
  }

  setVisible(visible: boolean) {
    this.visible = visible;
    this.billboards.show = visible;
    this.labels.show = visible;
  }

  destroy() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.viewer.scene.primitives.remove(this.billboards);
    this.viewer.scene.primitives.remove(this.labels);
  }
}
