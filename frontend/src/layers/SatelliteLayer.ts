/**
 * SatelliteLayer.ts — Real-time orbital propagation using satellite.js SGP4.
 *
 * Key architecture decisions (aligned with gods-eye reference):
 *  - PointPrimitiveCollection (not BillboardCollection) — PointPrimitives sit at a
 *    fixed ECEF world-space position and rotate with the globe, whereas canvas-based
 *    Billboards rendered with disableDepthTestDistance=INFINITY can appear screen-fixed.
 *  - preRender listener (not postRender) — positions are committed before Cesium draws
 *    the frame, so there is never a one-frame lag where the old position shows.
 *  - Solid colors only — no glow, no neon, no shadowBlur (matches user requirement).
 */

import * as Cesium from "cesium";
import * as satellite from "satellite.js";

const MAX_SATS = 150;
const ISS_NORAD = 25544;

// Solid, non-neon palette — red hero for ISS, muted violet for the rest
const COLOR_ISS     = Cesium.Color.fromCssColorString("#cc2222"); // solid red
const COLOR_NAV     = Cesium.Color.fromCssColorString("#5577dd"); // solid blue-indigo
const COLOR_GEO     = Cesium.Color.fromCssColorString("#8855cc"); // solid purple
const COLOR_DEFAULT = Cesium.Color.fromCssColorString("#7744bb"); // solid medium purple
const OUTLINE_COLOR = Cesium.Color.fromCssColorString("#1a1a2e"); // dark outline

interface TleRecord {
  name: string;
  line1: string;
  line2: string;
  norad_cat_id: number;
  group?: string;
}

interface SatEntry {
  satrec: satellite.SatRec;
  name: string;
  norad: number;
  point: Cesium.PointPrimitive;
  label: Cesium.Label;
}

function colorForGroup(group: string | undefined, noradId: number): Cesium.Color {
  if (noradId === ISS_NORAD) return COLOR_ISS;
  if (group === "gps-ops" || group === "glonass" || group === "galileo") return COLOR_NAV;
  if (group === "geo") return COLOR_GEO;
  return COLOR_DEFAULT;
}

export class SatelliteLayer {
  private viewer: Cesium.Viewer;
  private points: Cesium.PointPrimitiveCollection;
  private labels: Cesium.LabelCollection;
  private entries: SatEntry[] = [];
  private visible = true;
  private onCountUpdate: (n: number) => void;
  private preRenderHandler: (() => void) | null = null;

  constructor(viewer: Cesium.Viewer, onCountUpdate: (n: number) => void) {
    this.viewer = viewer;
    this.onCountUpdate = onCountUpdate;

    // PointPrimitiveCollection — renders as round dots in ECEF world space,
    // rotates correctly with the globe on every camera interaction.
    this.points = viewer.scene.primitives.add(
      new Cesium.PointPrimitiveCollection()
    );
    this.labels = viewer.scene.primitives.add(new Cesium.LabelCollection());

    this.fetchAndBuild();
  }

  private async fetchAndBuild() {
    try {
      const resp = await fetch(`/api/live/satellites/tle?limit=${MAX_SATS}`);
      if (!resp.ok) return;
      const data = await resp.json();
      const tles: TleRecord[] = data.satellites ?? [];

      for (const tle of tles.slice(0, MAX_SATS)) {
        try {
          const satrec = satellite.twoline2satrec(tle.line1, tle.line2);
          const color = colorForGroup(tle.group, tle.norad_cat_id);
          const isIss = tle.norad_cat_id === ISS_NORAD;

          const point = this.points.add({
            position: Cesium.Cartesian3.ZERO,
            pixelSize: isIss ? 10 : 6,
            color,
            outlineColor: OUTLINE_COLOR,
            outlineWidth: isIss ? 2 : 1,
            show: this.visible,
            // Disable depth test so points on the far side of the globe are
            // still visible — but this does NOT move them to screen-space.
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
            scaleByDistance: new Cesium.NearFarScalar(1_000_000, 1.4, 20_000_000, 0.5),
          });

          const label = this.labels.add({
            position: Cesium.Cartesian3.ZERO,
            text: tle.name.trim().substring(0, 20),
            font: "9px JetBrains Mono, monospace",
            fillColor: color,
            outlineColor: Cesium.Color.fromCssColorString("#000010"),
            outlineWidth: 2,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            pixelOffset: new Cesium.Cartesian2(10, 0),
            // Only show labels when zoomed close enough to reduce clutter
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 4_000_000),
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
            show: this.visible,
          });

          this.entries.push({
            satrec,
            name: tle.name,
            norad: tle.norad_cat_id,
            point,
            label,
          });
        } catch (_) {}
      }

      this.onCountUpdate(this.entries.length);
      this.startPropagation();
    } catch (_) {}
  }

  /**
   * Attach a preRender listener so satellite positions are updated BEFORE each
   * Cesium frame is drawn.  Using postRender (after the draw) means the globe
   * renders at the new camera angle but the satellite dots remain at their
   * previous ECEF coordinates for that one frame — making them appear to slip
   * against the globe surface while rotating.  preRender eliminates this lag.
   */
  private startPropagation() {
    const propagate = () => {
      if (!this.visible || this.entries.length === 0) return;

      const now = new Date();
      const gmst = satellite.gstime(now);

      for (const entry of this.entries) {
        try {
          const pv = satellite.propagate(entry.satrec, now);
          const posEci = pv.position;
          if (!posEci || typeof posEci === "boolean") continue;

          // Convert ECI → geodetic, then build a proper ECEF Cartesian3.
          // Cartesian3.fromDegrees places the point in the same rotating-Earth
          // frame that Cesium uses for all other primitives.
          const geo = satellite.eciToGeodetic(
            posEci as satellite.EciVec3<number>,
            gmst
          );
          const lon = satellite.degreesLong(geo.longitude);
          const lat = satellite.degreesLat(geo.latitude);
          const alt = geo.height * 1000; // km → m

          if (isNaN(lon) || isNaN(lat) || alt < 0) continue;

          const pos = Cesium.Cartesian3.fromDegrees(lon, lat, alt);
          entry.point.position = pos;
          entry.label.position = pos;
        } catch (_) {}
      }
    };

    this.preRenderHandler = propagate;
    this.viewer.scene.preRender.addEventListener(propagate);
  }

  setVisible(visible: boolean) {
    this.visible = visible;
    this.points.show = visible;
    this.labels.show = visible;
  }

  destroy() {
    if (this.preRenderHandler) {
      try {
        this.viewer.scene.preRender.removeEventListener(this.preRenderHandler);
      } catch (_) {}
      this.preRenderHandler = null;
    }
    try { this.viewer.scene.primitives.remove(this.points); } catch (_) {}
    try { this.viewer.scene.primitives.remove(this.labels); } catch (_) {}
  }
}
