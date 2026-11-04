/**
 * AircraftLayer.ts — Live aircraft billboard rendering on the Cesium globe.
 *
 * Polls /api/live/aircraft every 15 s.
 * Renders aircraft glyphs as BillboardCollection entries, rotated by heading.
 * Click-to-track shows a trailing polyline breadcrumb.
 */

import * as Cesium from "cesium";

const POLL_INTERVAL_MS = 15_000;

interface AircraftRecord {
  icao24: string;
  callsign?: string;
  latitude?: number;
  longitude?: number;
  baro_altitude?: number;
  true_track?: number;
  velocity?: number;
  on_ground: boolean;
  category: string;
}

interface Trail {
  positions: Cesium.Cartesian3[];
  line: Cesium.Primitive | null;
}

const CANVAS_CACHE = new Map<string, string>();

function buildAircraftCanvas(heading: number, category: string): string {
  const key = `${Math.round(heading / 10) * 10}:${category.startsWith("mil") ? "mil" : "civ"}`;
  if (CANVAS_CACHE.has(key)) return CANVAS_CACHE.get(key)!;

  const size = 32;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;

  ctx.save();
  ctx.translate(size / 2, size / 2);
  ctx.rotate(Cesium.Math.toRadians(heading));

  const isMil = category.startsWith("mil") || category === "reconnaissance";
  ctx.fillStyle = isMil ? "#ffb700" : "#00e5ff";
  ctx.shadowColor = isMil ? "#ffb700" : "#00e5ff";
  ctx.shadowBlur = 6;

  // Simple aircraft glyph
  ctx.beginPath();
  ctx.moveTo(0, -10);
  ctx.lineTo(3, -3);
  ctx.lineTo(9, 2);
  ctx.lineTo(5, 3);
  ctx.lineTo(3, 8);
  ctx.lineTo(5, 9);
  ctx.lineTo(0, 8);
  ctx.lineTo(-5, 9);
  ctx.lineTo(-3, 8);
  ctx.lineTo(-5, 3);
  ctx.lineTo(-9, 2);
  ctx.lineTo(-3, -3);
  ctx.closePath();
  ctx.fill();

  ctx.restore();
  const url = canvas.toDataURL();
  CANVAS_CACHE.set(key, url);
  return url;
}

export class AircraftLayer {
  private viewer: Cesium.Viewer;
  private billboards: Cesium.BillboardCollection;
  private labels: Cesium.LabelCollection;
  private entityMap: Map<string, { bb: Cesium.Billboard; label: Cesium.Label; pos: Cesium.Cartesian3 }> = new Map();
  private trails: Map<string, Trail> = new Map();
  private trackedIcao: string | null = null;
  private interval: ReturnType<typeof setInterval> | null = null;
  private visible = true;
  private onCountUpdate: (n: number) => void;

  constructor(viewer: Cesium.Viewer, onCountUpdate: (n: number) => void) {
    this.viewer = viewer;
    this.onCountUpdate = onCountUpdate;
    this.billboards = viewer.scene.primitives.add(new Cesium.BillboardCollection({ scene: viewer.scene }));
    this.labels     = viewer.scene.primitives.add(new Cesium.LabelCollection());

    this.poll();
    this.interval = setInterval(() => this.poll(), POLL_INTERVAL_MS);

    // Click handler for track selection
    viewer.screenSpaceEventHandler.setInputAction((click: { position: Cesium.Cartesian2 }) => {
      const picked = viewer.scene.pick(click.position);
      if (picked?.id?.startsWith?.("aircraft:")) {
        const icao = picked.id.replace("aircraft:", "");
        this.trackedIcao = this.trackedIcao === icao ? null : icao;
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  private async poll() {
    try {
      const resp = await fetch("/api/live/aircraft");
      if (!resp.ok) return;
      const data = await resp.json();
      const aircraft: AircraftRecord[] = data.aircraft ?? [];
      this.updateBillboards(aircraft);
    } catch (_) {}
  }

  private updateBillboards(aircraft: AircraftRecord[]) {
    const seenIcaos = new Set<string>();

    for (const ac of aircraft) {
      if (ac.latitude == null || ac.longitude == null) continue;

      const alt = ac.on_ground ? 10 : (ac.baro_altitude ?? 500);
      const pos = Cesium.Cartesian3.fromDegrees(ac.longitude, ac.latitude, alt);
      const heading = ac.true_track ?? 0;
      const icao = ac.icao24;
      seenIcaos.add(icao);

      const imageUrl = buildAircraftCanvas(heading, ac.category ?? "civilian");

      if (this.entityMap.has(icao)) {
        const entry = this.entityMap.get(icao)!;
        entry.bb.position = pos;
        entry.bb.image = imageUrl;
        entry.label.position = pos;
        entry.pos = pos;
        const bb = this.billboards.add({
          position: pos,
          image: imageUrl,
          id: `aircraft:${icao}`,
          width: 28,
          height: 28,
          scaleByDistance: new Cesium.NearFarScalar(1.5e6, 1.0, 1.5e7, 0.4),
          show: this.visible,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        });

        const label = this.labels.add({
          position: pos,
          text: ac.callsign ?? icao.toUpperCase(),
          font: "10px JetBrains Mono, monospace",
          fillColor: Cesium.Color.fromCssColorString("#00e5ff"),
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 2,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          pixelOffset: new Cesium.Cartesian2(0, -22),
          distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 2_500_000),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          show: this.visible,
        });

        this.entityMap.set(icao, { bb, label, pos });
      }

      // Update breadcrumb trail if this is the tracked aircraft
      if (this.trackedIcao === icao) {
        let trail = this.trails.get(icao);
        if (!trail) {
          trail = { positions: [], line: null };
          this.trails.set(icao, trail);
        }
        trail.positions.push(pos.clone());
        if (trail.positions.length > 120) trail.positions.shift();

        if (trail.line) this.viewer.scene.primitives.remove(trail.line);
        trail.line = this.viewer.scene.primitives.add(
          new Cesium.Primitive({
            geometryInstances: new Cesium.GeometryInstance({
              geometry: new Cesium.PolylineGeometry({
                positions: trail.positions,
                width: 1.5,
              }),
            }),
            appearance: new Cesium.PolylineColorAppearance({
              translucent: false,
            }),
          })
        );
      }
    }

    // Remove stale entities
    for (const [icao, entry] of this.entityMap.entries()) {
      if (!seenIcaos.has(icao)) {
        this.billboards.remove(entry.bb);
        this.labels.remove(entry.label);
        this.entityMap.delete(icao);
        const trail = this.trails.get(icao);
        if (trail?.line) this.viewer.scene.primitives.remove(trail.line);
        this.trails.delete(icao);
      }
    }

    this.onCountUpdate(this.entityMap.size);
  }

  setVisible(visible: boolean) {
    this.visible = visible;
    this.billboards.show = visible;
    this.labels.show = visible;
  }

  destroy() {
    if (this.interval) clearInterval(this.interval);
    this.viewer.scene.primitives.remove(this.billboards);
    this.viewer.scene.primitives.remove(this.labels);
    for (const trail of this.trails.values()) {
      if (trail.line) this.viewer.scene.primitives.remove(trail.line);
    }
  }
}
