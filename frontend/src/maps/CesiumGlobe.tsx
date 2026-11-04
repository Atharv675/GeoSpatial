/**
 * CesiumGlobe.tsx — Exact GODS Eye UI Replication with Full Multi-Domain Telemetry
 *
 * Replicates the authentic God's Eye View architecture:
 * - #title-bar (with Logo, GOD'S EYE VIEW branding, and subtitle)
 * - #style-indicator (ACTIVE STYLE: NORMAL, CRT, NVG, FLIR, ANIME, NOIR, SNOW)
 * - #top-center-actions (layers_clear, share, view_in_ar tilt, north navigation, reset globe)
 * - #command-dock (Unified bottom dock with Location Bar tray and Visual Presets tray)
 * - #left-panel-stack (#data-panel with 4 categorized domains, #cctv-panel, #weather-panel, #radio-panel)
 * - #pp-toggles (Right rail DISPLAY panel with HUD layout, Cyber Sonar sliders, and DETECT overlay)
 * - #cockpit-entry & #cockpit-hud (Fighter jet flight HUD with pitch ladder, compass tape, airspeed/altimeter tapes)
 * - #context (Target Telemetry Inspection drawer / card)
 * - Wires all 17 live layers from backend and mock telemetry
 */

import { useCallback, useEffect, useRef, useState } from "react";
import * as Cesium from "cesium";

// Core Layer Imports
import { AircraftLayer } from "../layers/AircraftLayer";
import { MilitaryLayer, type MilitaryTrack } from "../layers/MilitaryLayer";
import { VesselLayer } from "../layers/VesselLayer";
import { SubmarineCableLayer, type SubmarineCable } from "../layers/SubmarineCableLayer";
import { SatelliteLayer } from "../layers/SatelliteLayer";
import { LaunchLayer, type SpaceLaunch } from "../layers/LaunchLayer";
import { EarthquakeLayer, type EarthquakeRecord } from "../layers/EarthquakeLayer";
import { FirmsLayer, type FirmsHotspot } from "../layers/FirmsLayer";
import { CycloneLayer, type CycloneRecord } from "../layers/CycloneLayer";
import { WeatherRadarLayer } from "../layers/WeatherRadarLayer";
import { CctvLayer } from "../layers/CctvLayer";
import { TransitLayer, type TransitVehicle } from "../layers/TransitLayer";
import { InstallationLayer, type DefenseInstallation } from "../layers/InstallationLayer";
import { GnssLayer, type GnssZone } from "../layers/GnssLayer";
import { AirQualityLayer, type AqiStation } from "../layers/AirQualityLayer";
import { RadioLayer, type RadioStation } from "../layers/RadioLayer";
import { PerimeterLayer, type TacticalPerimeter } from "../layers/PerimeterLayer";
// @ts-expect-error JS module without declaration
import { registerDataCredits } from "../data/dataCredits";
import { VisualShaderManager } from "./visualShaders";
import type { AoiFeature } from "../api/types";

/* ── Strategic Locations ─────────────────────────────────────────────────── */
const STRATEGIC_LOCATIONS = [
  { name: "Taiwan Strait", lat: 24.5, lon: 119.8, alt: 750_000, pitch: -60 },
  { name: "Bab el-Mandeb", lat: 12.6, lon: 43.4, alt: 600_000, pitch: -55 },
  { name: "Strait of Hormuz", lat: 26.5, lon: 56.4, alt: 650_000, pitch: -55 },
  { name: "Suez Canal", lat: 30.5, lon: 32.3, alt: 450_000, pitch: -50 },
  { name: "Port of Beirut", lat: 33.9, lon: 35.5, alt: 180_000, pitch: -45 },
  { name: "Tokyo", lat: 35.676, lon: 139.650, alt: 220_000, pitch: -50 },
  { name: "Kyiv", lat: 50.450, lon: 30.523, alt: 350_000, pitch: -55 },
  { name: "London", lat: 51.507, lon: -0.127, alt: 250_000, pitch: -50 },
  { name: "San Francisco", lat: 37.774, lon: -122.419, alt: 220_000, pitch: -50 },
  { name: "Singapore", lat: 1.352, lon: 103.819, alt: 300_000, pitch: -55 },
];

export type VisualStyle = "normal" | "retro" | "surveillance" | "thermal" | "anime" | "noir" | "snow";

interface ContactRoster {
  aircraft: number;
  military: number;
  vessels: number;
  cables: number;
  satellites: number;
  launches: number;
  earthquakes: number;
  firms: number;
  cyclones: number;
  cctv: number;
  transit: number;
  installations: number;
  gnss: number;
  airquality: number;
  radio: number;
  perimeters: number;
}

interface TargetInspection {
  type: string;
  title: string;
  subtitle: string;
  coordinates: [number, number];
  metrics: { label: string; value: string | number }[];
  raw?: any;
}

interface CctvCamera {
  id: string;
  name: string;
  imageUrl: string;
  agency: string;
  latitude: number;
  longitude: number;
}

interface CesiumGlobeProps {
  aois?: AoiFeature[];
  selectedAoiId?: string | null;
  onSelectAoi?: (id: string) => void;
  onSwitchTo2D?: () => void;
}

export default function CesiumGlobe({
  aois = [],
  selectedAoiId,
  onSelectAoi,
  onSwitchTo2D,
}: CesiumGlobeProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);

  // Layer instances
  const aircraftLayerRef = useRef<AircraftLayer | null>(null);
  const militaryLayerRef = useRef<MilitaryLayer | null>(null);
  const vesselLayerRef = useRef<VesselLayer | null>(null);
  const cableLayerRef = useRef<SubmarineCableLayer | null>(null);
  const satLayerRef = useRef<SatelliteLayer | null>(null);
  const launchLayerRef = useRef<LaunchLayer | null>(null);
  const earthquakeLayerRef = useRef<EarthquakeLayer | null>(null);
  const firmsLayerRef = useRef<FirmsLayer | null>(null);
  const cycloneLayerRef = useRef<CycloneLayer | null>(null);
  const weatherLayerRef = useRef<WeatherRadarLayer | null>(null);
  const cctvLayerRef = useRef<CctvLayer | null>(null);
  const transitLayerRef = useRef<TransitLayer | null>(null);
  const installLayerRef = useRef<InstallationLayer | null>(null);
  const gnssLayerRef = useRef<GnssLayer | null>(null);
  const aqiLayerRef = useRef<AirQualityLayer | null>(null);
  const radioLayerRef = useRef<RadioLayer | null>(null);
  const perimLayerRef = useRef<PerimeterLayer | null>(null);
  const aoiDataSourcesRef = useRef<Cesium.GeoJsonDataSource[]>([]);
  const shaderManagerRef = useRef<VisualShaderManager | null>(null);
  const active3DTilesetRef = useRef<Cesium.Cesium3DTileset | null>(null);
  const [detectionOverlay, setDetectionOverlay] = useState(false);

  // Telemetry & UI States
  const [hudCoords, setHudCoords] = useState({ lat: 30, lon: 35, alt: 11000000, pitch: -90, heading: 0, roll: 0 });
  const [activeStyle, setActiveStyle] = useState<VisualStyle>("normal");
  const [activeMapSource, setActiveMapSource] = useState<"3d" | "esri" | "osm">(
    (import.meta.env.VITE_GOOGLE_MAPS_API_KEY || import.meta.env.VITE_CESIUM_ION_TOKEN) ? "3d" : "esri"
  );
  const [activeLocation, setActiveLocation] = useState("Global Orbit");
  const [searchQuery, setSearchQuery] = useState("");

  // Dock & Rail Tray Expansion States
  const [presetsExpanded, setPresetsExpanded] = useState(false);
  const [locationExpanded, setLocationExpanded] = useState(false);
  const [dataPanelCollapsed, setDataPanelCollapsed] = useState(false);
  const [cctvPanelCollapsed, setCctvPanelCollapsed] = useState(true);
  const [weatherPanelCollapsed, setWeatherPanelCollapsed] = useState(true);
  const [radioPanelCollapsed, setRadioPanelCollapsed] = useState(true);
  const [ppTogglesCollapsed, setPpTogglesCollapsed] = useState(true);
  const [cockpitActive, setCockpitActive] = useState(false);
  const [hudEnabled, setHudEnabled] = useState(true);
  const [sonarActive, setSonarActive] = useState(true);
  const [sonarRings, setSonarRings] = useState(8);
  const [sonarPower, setSonarPower] = useState(70);
  const [hudLayout, setHudLayout] = useState<"tactical" | "operator" | "minimal" | "cyber">("tactical");

  // Roster counts
  const [roster, setRoster] = useState<ContactRoster>({
    aircraft: 0,
    military: 0,
    vessels: 0,
    cables: 5,
    satellites: 0,
    launches: 0,
    earthquakes: 0,
    firms: 0,
    cyclones: 0,
    cctv: 0,
    transit: 0,
    installations: 12,
    gnss: 5,
    airquality: 8,
    radio: 6,
    perimeters: 4,
  });

  // Layer visibility toggles — defaults tuned to God's Eye clean tactical view
  const [layers, setLayers] = useState({
    satellites: true,
    aircraft: true,
    military: true,
    vessels: false,
    transit: false,
    launches: true,
    cables: true,
    installations: false,
    gnss: false,
    perimeters: false,
    radio: false,
    earthquakes: false,
    firms: false,
    cyclones: false,
    weather: false,
    airquality: false,
    cctv: false,
    aois: true,
  });

  // Active target inspection & active CCTV
  const [activeInspection, setActiveInspection] = useState<TargetInspection | null>(null);
  const [activeCctv, setActiveCctv] = useState<CctvCamera | null>(null);

  /* ── Initialise Cesium Viewer ───────────────────────────────────────── */
  useEffect(() => {
    if (!containerRef.current || viewerRef.current) return;

    Cesium.Ion.defaultAccessToken =
      import.meta.env.VITE_CESIUM_ION_TOKEN || "";

    const creditContainer = document.createElement("div");
    creditContainer.style.display = "none";

    let viewer: Cesium.Viewer;
    try {
      viewer = new Cesium.Viewer(containerRef.current, {
        baseLayer: false,
        terrainProvider: new Cesium.EllipsoidTerrainProvider(),
        animation: false,
        timeline: false,
        baseLayerPicker: false,
        navigationHelpButton: false,
        homeButton: false,
        geocoder: false,
        fullscreenButton: false,
        vrButton: false,
        infoBox: false,
        selectionIndicator: false,
        sceneModePicker: false,
        skyAtmosphere: new Cesium.SkyAtmosphere(),
        shouldAnimate: true,
        creditContainer: creditContainer,
      });
    } catch (err) {
      console.error("[CesiumGlobe] Viewer init failed:", err);
      return;
    }

    viewer.scene.globe.enableLighting = true;
    try {
      viewer.scene.skyBox = Cesium.SkyBox.createEarthSkyBox();
    } catch (_) {}

    // Camera controller tweaks for a natural zoom/pan experience
    const ctrl = viewer.scene.screenSpaceCameraController;
    ctrl.minimumZoomDistance = 150;          // allow zoom down to ~150 m
    ctrl.maximumZoomDistance = 30_000_000;   // cap at ~30 000 km (globe visible)
    ctrl.enableCollisionDetection = false;   // don't snap camera above terrain

    // Terrain upgrade if Cesium ion token is provided
    if (import.meta.env.VITE_CESIUM_ION_TOKEN) {
      Cesium.createWorldTerrainAsync()
        .then((terrain) => {
          if (!viewer.isDestroyed()) viewer.terrainProvider = terrain;
        })
        .catch(() => {});
    }

    // Initial camera position
    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(35.0, 31.0, 11_000_000),
      orientation: {
        heading: 0,
        pitch: Cesium.Math.toRadians(-90),
        roll: 0,
      },
    });

    viewerRef.current = viewer;

    // Register all in-app third-party data attribution from DATA_SOURCES.md
    try {
      registerDataCredits(viewer);
    } catch (_) {}

    // Boot GLSL visual shader post-processing pipeline
    try {
      shaderManagerRef.current = new VisualShaderManager(viewer);
    } catch (err) {
      console.warn("[CesiumGlobe] VisualShaderManager init failed:", err);
    }

    /* ── Mount Multi-Domain Layers ────────────────────────────────────── */
    aircraftLayerRef.current = new AircraftLayer(viewer, (n) =>
      setRoster((r) => ({ ...r, aircraft: n }))
    );

    militaryLayerRef.current = new MilitaryLayer(
      viewer,
      (n) => setRoster((r) => ({ ...r, military: n })),
      (track: MilitaryTrack) => {
        setActiveInspection({
          type: "MILITARY COMBAT / RECON AIRCRAFT",
          title: track.callsign || track.icao24.toUpperCase(),
          subtitle: `${track.origin_country || "Unknown Origin"} • Category: ${track.category.toUpperCase()}`,
          coordinates: [track.longitude, track.latitude],
          metrics: [
            { label: "ICAO-24", value: track.icao24 },
            { label: "Altitude", value: track.baro_altitude ? `${Math.round(track.baro_altitude)} m` : "N/A" },
            { label: "Velocity", value: track.velocity ? `${Math.round(track.velocity * 1.94384)} kts` : "N/A" },
            { label: "Heading", value: track.true_track ? `${Math.round(track.true_track)}°` : "N/A" },
          ],
        });
        setActiveCctv(null);
      }
    );

    vesselLayerRef.current = new VesselLayer(viewer, (n) =>
      setRoster((r) => ({ ...r, vessels: n }))
    );

    cableLayerRef.current = new SubmarineCableLayer(
      viewer,
      (n) => setRoster((r) => ({ ...r, cables: n })),
      (cable: SubmarineCable) => {
        setActiveInspection({
          type: "SUBMARINE FIBER OPTIC CABLE",
          title: cable.name,
          subtitle: `Design Capacity: ${cable.capacity} • Status: ${cable.status.toUpperCase()}`,
          coordinates: [cable.coordinates[0][0], cable.coordinates[0][1]],
          metrics: [
            { label: "System ID", value: cable.id },
            { label: "Capacity", value: cable.capacity },
            { label: "Domain", value: "Trans-oceanic Subsea Fiber" },
          ],
        });
      }
    );

    satLayerRef.current = new SatelliteLayer(viewer, (n) =>
      setRoster((r) => ({ ...r, satellites: n }))
    );

    launchLayerRef.current = new LaunchLayer(
      viewer,
      (n) => setRoster((r) => ({ ...r, launches: n })),
      (l: SpaceLaunch) => {
        setActiveInspection({
          type: "SPACE LAUNCH MISSION",
          title: l.name,
          subtitle: `${l.lsp_name || "Commercial Launch"} • Pad: ${l.pad.name}`,
          coordinates: [l.pad.longitude, l.pad.latitude],
          metrics: [
            { label: "Status", value: l.status.toUpperCase() },
            { label: "NET Window", value: new Date(l.net).toLocaleString() },
            { label: "Location", value: l.pad.location },
            { label: "Orbit Target", value: l.mission?.orbit || "LEO" },
          ],
        });
      }
    );

    earthquakeLayerRef.current = new EarthquakeLayer(
      viewer,
      (n) => setRoster((r) => ({ ...r, earthquakes: n })),
      (quake: EarthquakeRecord) => {
        setActiveInspection({
          type: "SEISMIC EVENT / EARTHQUAKE",
          title: `M ${quake.magnitude.toFixed(1)} — ${quake.place}`,
          subtitle: `Focal Depth: ${quake.depth_km} km • USGS Alert: ${(quake.alert || "None").toUpperCase()}`,
          coordinates: [quake.longitude, quake.latitude],
          metrics: [
            { label: "Magnitude", value: `M ${quake.magnitude.toFixed(1)}` },
            { label: "Depth", value: `${quake.depth_km} km` },
            { label: "Tsunami Warning", value: quake.tsunami ? "YES" : "No" },
            { label: "Origin Time", value: new Date(quake.time).toLocaleTimeString() },
          ],
        });
        setActiveCctv(null);
      }
    );

    firmsLayerRef.current = new FirmsLayer(
      viewer,
      (n) => setRoster((r) => ({ ...r, firms: n })),
      (spot: FirmsHotspot) => {
        setActiveInspection({
          type: "NASA FIRMS ACTIVE THERMAL HOTSPOT",
          title: `Radiative Power: ${spot.frp} MW`,
          subtitle: `Sensor: ${spot.satellite} • Confidence: ${spot.confidence.toUpperCase()}`,
          coordinates: [spot.longitude, spot.latitude],
          metrics: [
            { label: "Brightness Temp", value: `${spot.brightness} K` },
            { label: "Fire Radiative Power", value: `${spot.frp} MW` },
            { label: "Acquisition Time", value: `${spot.acq_date} ${spot.acq_time} UTC` },
            { label: "Satellite Sensor", value: spot.satellite },
          ],
        });
      }
    );

    cycloneLayerRef.current = new CycloneLayer(
      viewer,
      (n) => setRoster((r) => ({ ...r, cyclones: n })),
      (c: CycloneRecord) => {
        setActiveInspection({
          type: "TROPICAL CYCLONE / HURRICANE",
          title: `${c.classification} ${c.name.toUpperCase()}`,
          subtitle: `Wind Speed: ${c.intensity_mph} mph • Barometric: ${c.pressure_mb} mb`,
          coordinates: [c.longitude, c.latitude],
          metrics: [
            { label: "Max Wind Speed", value: `${c.intensity_mph} mph` },
            { label: "Central Pressure", value: `${c.pressure_mb} mb` },
            { label: "Track Motion", value: `${c.movement_dir} at ${c.movement_speed_mph} mph` },
          ],
        });
      }
    );

    weatherLayerRef.current = new WeatherRadarLayer(viewer);

    cctvLayerRef.current = new CctvLayer(viewer, (cam) => {
      setActiveCctv(cam);
      setActiveInspection(null);
    });

    transitLayerRef.current = new TransitLayer(
      viewer,
      (n) => setRoster((r) => ({ ...r, transit: n })),
      (veh: TransitVehicle) => {
        setActiveInspection({
          type: "PUBLIC TRANSIT VEHICLE",
          title: `Vehicle ${veh.id} • Route ${veh.route_id || "Direct"}`,
          subtitle: `Agency: ${(veh.agency || "MBTA").toUpperCase()} • Speed: ${veh.speed_kmh ? `${Math.round(veh.speed_kmh * 0.621371)} mph` : "Stopped"}`,
          coordinates: [veh.longitude, veh.latitude],
          metrics: [
            { label: "Vehicle ID", value: veh.id },
            { label: "Route", value: veh.route_id || "Express" },
            { label: "Bearing", value: veh.bearing ? `${Math.round(veh.bearing)}°` : "N/A" },
          ],
        });
        setActiveCctv(null);
      }
    );

    installLayerRef.current = new InstallationLayer(
      viewer,
      (n) => setRoster((r) => ({ ...r, installations: n })),
      (inst: DefenseInstallation) => {
        setActiveInspection({
          type: "STRATEGIC DEFENSE BASE / INSTALLATION",
          title: inst.name,
          subtitle: `${inst.country} • Type: ${inst.type}`,
          coordinates: [inst.longitude, inst.latitude],
          metrics: [
            { label: "Command Type", value: inst.type },
            { label: "Jurisdiction", value: inst.country },
            { label: "Status", value: inst.status.toUpperCase() },
            { label: "Elevation", value: `${inst.elevation} m` },
          ],
        });
      }
    );

    gnssLayerRef.current = new GnssLayer(
      viewer,
      (n) => setRoster((r) => ({ ...r, gnss: n })),
      (zone: GnssZone) => {
        setActiveInspection({
          type: "ELECTRONIC WARFARE / GNSS DENIAL",
          title: zone.name,
          subtitle: `Severity: ${zone.severity} • Radius: ${zone.radius_km} km`,
          coordinates: [zone.center[0], zone.center[1]],
          metrics: [
            { label: "Threat Type", value: zone.type },
            { label: "Interference Radius", value: `${zone.radius_km} km` },
            { label: "Reported Anomalies", value: zone.reported_anomalies },
          ],
        });
      }
    );

    aqiLayerRef.current = new AirQualityLayer(
      viewer,
      (n) => setRoster((r) => ({ ...r, airquality: n })),
      (st: AqiStation) => {
        setActiveInspection({
          type: "AIR QUALITY (AQI) SENSOR",
          title: `${st.city}, ${st.country}`,
          subtitle: `AQI: ${st.aqi} • ${st.category}`,
          coordinates: [st.longitude, st.latitude],
          metrics: [
            { label: "AQI Value", value: st.aqi },
            { label: "PM2.5", value: `${st.pm25} µg/m³` },
            { label: "Category", value: st.category },
          ],
        });
      }
    );

    radioLayerRef.current = new RadioLayer(
      viewer,
      (n) => setRoster((r) => ({ ...r, radio: n })),
      (st: RadioStation) => {
        setActiveInspection({
          type: "WEBSDR / ATC AIRBAND STATION",
          title: st.name,
          subtitle: `Frequency: ${st.frequency} • Sector: ${st.type}`,
          coordinates: [st.longitude, st.latitude],
          metrics: [
            { label: "Frequency", value: st.frequency },
            { label: "Sector", value: st.type },
            { label: "Status", value: st.status.toUpperCase() },
          ],
        });
      }
    );

    perimLayerRef.current = new PerimeterLayer(
      viewer,
      (n) => setRoster((r) => ({ ...r, perimeters: n })),
      (p: TacticalPerimeter) => {
        setActiveInspection({
          type: "TACTICAL PERIMETER / ADIZ",
          title: p.name,
          subtitle: `Type: ${p.type} • Classification: ${p.classification}`,
          coordinates: [p.coordinates[0][0], p.coordinates[0][1]],
          metrics: [
            { label: "Zone Type", value: p.type },
            { label: "Classification", value: p.classification },
            { label: "Corridor Points", value: p.coordinates.length },
          ],
        });
      }
    );

    // Camera Telemetry Listener
    viewer.camera.changed.addEventListener(() => {
      const pos = viewer.camera.positionCartographic;
      setHudCoords({
        lat: Cesium.Math.toDegrees(pos.latitude),
        lon: Cesium.Math.toDegrees(pos.longitude),
        alt: Math.round(pos.height),
        pitch: Math.round(Cesium.Math.toDegrees(viewer.camera.pitch)),
        heading: Math.round(Cesium.Math.toDegrees(viewer.camera.heading)),
        roll: Math.round(Cesium.Math.toDegrees(viewer.camera.roll)),
      });
    });

    return () => {
      aircraftLayerRef.current?.destroy();
      militaryLayerRef.current?.destroy();
      vesselLayerRef.current?.destroy();
      cableLayerRef.current?.destroy();
      satLayerRef.current?.destroy();
      launchLayerRef.current?.destroy();
      earthquakeLayerRef.current?.destroy();
      firmsLayerRef.current?.destroy();
      cycloneLayerRef.current?.destroy();
      weatherLayerRef.current?.destroy();
      cctvLayerRef.current?.destroy();
      transitLayerRef.current?.destroy();
      installLayerRef.current?.destroy();
      gnssLayerRef.current?.destroy();
      aqiLayerRef.current?.destroy();
      radioLayerRef.current?.destroy();
      perimLayerRef.current?.destroy();
      shaderManagerRef.current?.destroy();

      if (!viewer.isDestroyed()) {
        viewer.destroy();
      }
      viewerRef.current = null;
    };
  }, []);

  /* ── Keyboard Shortcuts (God's Eye View authentic bindings) ─────────── */
  useEffect(() => {
    const STYLE_KEYS: Record<string, VisualStyle> = {
      '1': 'normal', '2': 'retro', '3': 'surveillance',
      '4': 'thermal', '5': 'anime', '6': 'noir', '7': 'snow',
    };
    const onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      const inForm = tag === 'input' || tag === 'textarea' || tag === 'select';
      if (inForm && e.key !== 'Escape') return;

      // 1-7: visual presets
      if (STYLE_KEYS[e.key]) {
        const s = STYLE_KEYS[e.key];
        setActiveStyle(s);
        shaderManagerRef.current?.setStyle(s);
        return;
      }

      const key = e.key.toLowerCase();
      // C: toggle cockpit HUD
      if (key === 'c') { setCockpitActive((v) => !v); return; }
      // H: toggle HUD overlay
      if (key === 'h') { setHudEnabled((v) => !v); return; }
      // D: toggle detection overlay bounding boxes
      if (key === 'd') { setDetectionOverlay((v) => !v); return; }
      // G: reset globe (use ref directly to avoid dependency cycle)
      if (key === 'g') {
        const v = viewerRef.current;
        if (v && !v.isDestroyed()) {
          v.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(40.0, 20.0, 16_000_000),
            orientation: { heading: 0, pitch: Cesium.Math.toRadians(-90), roll: 0 },
            duration: 2.0,
          });
        }
        return;
      }
      // Escape: close context card
      if (e.key === 'Escape') {
        setActiveInspection(null);
        setActiveCctv(null);
        return;
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, []);  // stable — only refs and state setters used

  /* ── AOI Boundaries ─────────────────────────────────────────────────── */
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;

    for (const ds of aoiDataSourcesRef.current) {
      viewer.dataSources.remove(ds, true);
    }
    aoiDataSourcesRef.current = [];

    if (!layers.aois || aois.length === 0) return;

    aois.forEach(async (feature) => {
      try {
        const isSelected = feature.properties.aoi_id === selectedAoiId;
        const strokeColor = isSelected ? "#00ffff" : "#00e5ff";
        const strokeAlpha = isSelected ? 1.0 : 0.75;
        const fillAlpha = isSelected ? 0.22 : 0.08;

        const ds = new Cesium.GeoJsonDataSource(feature.properties.aoi_id);
        await ds.load(feature, {
          stroke: Cesium.Color.fromCssColorString(strokeColor).withAlpha(strokeAlpha),
          fill: Cesium.Color.fromCssColorString(strokeColor).withAlpha(fillAlpha),
          strokeWidth: isSelected ? 3 : 2,
          clampToGround: true,
        });

        if (!viewer.isDestroyed()) {
          viewer.dataSources.add(ds);
          aoiDataSourcesRef.current.push(ds);
        }
      } catch (_) {}
    });

    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction((click: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
      const picked = viewer.scene.pick(click.position);
      if (Cesium.defined(picked) && picked.id) {
        const entityId = picked.id.id || picked.id.name;
        if (entityId && typeof entityId === "string") {
          const match = aois.find((a) => a.properties.aoi_id === entityId);
          if (match && onSelectAoi) {
            onSelectAoi(match.properties.aoi_id);
          }
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    return () => {
      if (!handler.isDestroyed()) {
        handler.destroy();
      }
    };
  }, [aois, selectedAoiId, layers.aois, onSelectAoi]);

  /* ── Synchronize Layer Visibility ───────────────────────────────────── */
  useEffect(() => {
    aircraftLayerRef.current?.setVisible(layers.aircraft);
    militaryLayerRef.current?.setVisible(layers.military);
    vesselLayerRef.current?.setVisible(layers.vessels);
    cableLayerRef.current?.setVisible(layers.cables);
    satLayerRef.current?.setVisible(layers.satellites);
    launchLayerRef.current?.setVisible(layers.launches);
    earthquakeLayerRef.current?.setVisible(layers.earthquakes);
    firmsLayerRef.current?.setVisible(layers.firms);
    cycloneLayerRef.current?.setVisible(layers.cyclones);
    weatherLayerRef.current?.setVisible(layers.weather);
    cctvLayerRef.current?.setVisible(layers.cctv);
    transitLayerRef.current?.setVisible(layers.transit);
    installLayerRef.current?.setVisible(layers.installations);
    gnssLayerRef.current?.setVisible(layers.gnss);
    aqiLayerRef.current?.setVisible(layers.airquality);
    radioLayerRef.current?.setVisible(layers.radio);
    perimLayerRef.current?.setVisible(layers.perimeters);
    for (const ds of aoiDataSourcesRef.current) {
      ds.show = layers.aois;
    }
  }, [layers]);

  /* ── Visual Presets — CSS class + GLSL PostProcessStage ────────────── */
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.classList.remove(
      "style-normal",
      "style-retro",
      "style-surveillance",
      "style-thermal",
      "style-anime",
      "style-noir",
      "style-snow"
    );
    el.classList.add(`style-${activeStyle}`);
    // Also drive the Cesium PostProcessStage
    shaderManagerRef.current?.setStyle(activeStyle);
  }, [activeStyle]);

  /* ── Dynamic Map Source / Imagery & 3D Tiles Switching ──────────────── */
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;

    const googleKey = (import.meta.env.VITE_GOOGLE_MAPS_API_KEY || "").trim();
    const ionToken = (import.meta.env.VITE_CESIUM_ION_TOKEN || "").trim();

    // Clean up active 3D tileset if one was mounted
    if (active3DTilesetRef.current) {
      try {
        viewer.scene.primitives.remove(active3DTilesetRef.current);
      } catch (_) {}
      active3DTilesetRef.current = null;
    }

    const loadEsri = () => {
      Cesium.ArcGisMapServerImageryProvider.fromUrl(
        "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer",
        { enablePickFeatures: false }
      ).then((esri) => {
        if (!viewer.isDestroyed()) {
          viewer.imageryLayers.removeAll();
          viewer.imageryLayers.addImageryProvider(esri);
        }
      }).catch((err) => {
        console.warn("[CesiumGlobe] Esri World Imagery fallback to OSM:", err);
        if (!viewer.isDestroyed()) {
          viewer.imageryLayers.removeAll();
          viewer.imageryLayers.addImageryProvider(
            new Cesium.OpenStreetMapImageryProvider({ url: "https://tile.openstreetmap.org/" })
          );
        }
      });
    };

    if (activeMapSource === "3d" && (googleKey || ionToken)) {
      const load3D = async () => {
        try {
          let tileset: Cesium.Cesium3DTileset;
          if (googleKey) {
            tileset = await Cesium.createGooglePhotorealistic3DTileset({
              key: googleKey,
              onlyUsingWithGoogleGeocoder: true,
            });
          } else {
            const resource = await Cesium.IonResource.fromAssetId(2275207, {
              accessToken: ionToken,
            });
            tileset = await Cesium.Cesium3DTileset.fromUrl(resource);
          }
          if (!viewer.isDestroyed()) {
            viewer.imageryLayers.removeAll();
            active3DTilesetRef.current = viewer.scene.primitives.add(tileset);
          }
        } catch (err) {
          console.warn("[CesiumGlobe] 3D Photorealistic tileset load failed, falling back to Esri Satellite:", err);
          loadEsri();
        }
      };
      load3D();
    } else if (activeMapSource === "osm") {
      viewer.imageryLayers.removeAll();
      viewer.imageryLayers.addImageryProvider(
        new Cesium.OpenStreetMapImageryProvider({ url: "https://tile.openstreetmap.org/" })
      );
    } else {
      loadEsri();
    }
  }, [activeMapSource]);

  /* ── Camera Navigation ──────────────────────────────────────────────── */
  const flyTo = useCallback((lon: number, lat: number, alt: number = 250_000, pitch: number = -55) => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(lon, lat, alt),
      orientation: {
        heading: 0,
        pitch: Cesium.Math.toRadians(pitch),
        roll: 0,
      },
      duration: 2.0,
    });
  }, []);

  const resetGlobe = () => flyTo(40.0, 20.0, 16_000_000, -90);
  const resetNorth = () => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;
    viewer.camera.setView({
      orientation: {
        heading: 0,
        pitch: viewer.camera.pitch,
        roll: 0,
      },
    });
  };
  const toggleTilt = () => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;
    const currentPitch = Cesium.Math.toDegrees(viewer.camera.pitch);
    const targetPitch = currentPitch < -70 ? -45 : -90;
    viewer.camera.flyTo({
      destination: viewer.camera.position,
      orientation: {
        heading: viewer.camera.heading,
        pitch: Cesium.Math.toRadians(targetPitch),
        roll: 0,
      },
      duration: 1.2,
    });
  };
  const clearAllLayers = () => {
    setLayers({
      satellites: false,
      aircraft: false,
      military: false,
      vessels: false,
      transit: false,
      launches: false,
      cables: false,
      installations: false,
      gnss: false,
      perimeters: false,
      radio: false,
      earthquakes: false,
      firms: false,
      cyclones: false,
      weather: false,
      airquality: false,
      cctv: false,
      aois: false,
    });
  };

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        overflow: "hidden",
        background: "#0a0a0f",
      }}
    >
      {/* ── Cesium Canvas ── */}
      <div id="cesiumContainer" ref={containerRef} style={{ width: "100%", height: "100%" }} />

      {/* ── D KEY: Detection / Target Acquisition Overlay ── */}
      {detectionOverlay && (
        <div
          id="detection-overlay"
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            zIndex: 50,
          }}
        >
          {/* Corner bracket reticles — tactical target acquisition */}
          {[
            { top: "18%", left: "12%", w: 90, h: 60, color: "#00e5ff", label: "AIRCRAFT" },
            { top: "42%", left: "60%", w: 70, h: 50, color: "#ffb700", label: "VESSEL" },
            { top: "65%", left: "30%", w: 80, h: 55, color: "#ff3b5c", label: "MILITARY" },
          ].map((t, i) => (
            <div
              key={i}
              style={{
                position: "absolute",
                top: t.top,
                left: t.left,
                width: t.w,
                height: t.h,
                border: `1px solid ${t.color}`,
                boxShadow: `0 0 8px ${t.color}55`,
                animation: "detection-pulse 1.8s ease-in-out infinite",
              }}
            >
              <div style={{ position: "absolute", top: -1, left: -1, width: 10, height: 10, borderTop: `2px solid ${t.color}`, borderLeft: `2px solid ${t.color}` }} />
              <div style={{ position: "absolute", top: -1, right: -1, width: 10, height: 10, borderTop: `2px solid ${t.color}`, borderRight: `2px solid ${t.color}` }} />
              <div style={{ position: "absolute", bottom: -1, left: -1, width: 10, height: 10, borderBottom: `2px solid ${t.color}`, borderLeft: `2px solid ${t.color}` }} />
              <div style={{ position: "absolute", bottom: -1, right: -1, width: 10, height: 10, borderBottom: `2px solid ${t.color}`, borderRight: `2px solid ${t.color}` }} />
              <span style={{ position: "absolute", top: -18, left: 0, fontSize: "0.58rem", fontFamily: "var(--font-mono)", color: t.color, letterSpacing: "1px" }}>{t.label}</span>
            </div>
          ))}
          <div style={{ position: "absolute", top: 12, left: "50%", transform: "translateX(-50%)", fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "#ff3b5c", letterSpacing: "2px", textShadow: "0 0 8px #ff3b5c" }}>
            ◈ DETECTION ACTIVE — PRESS D TO DISABLE
          </div>
        </div>
      )}

      {/* ── 1. TITLE BAR (Top Left) ── */}
      <div id="title-bar">
        <div className="title-glow"></div>
        <h1>
          <span className="title-logo brand-logo" aria-hidden="true">
            <img src="/logo.svg" alt="" />
          </span>
          <span>
            GOD'S EYE <span className="title-accent">VIEW</span>
          </span>
        </h1>
        <p className="subtitle">NO PLACE LEFT BEHIND</p>

        {/* 2D SAR STUDIO Hop Pill */}
        {onSwitchTo2D && (
          <button
            onClick={onSwitchTo2D}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              marginTop: 6,
              background: "rgba(0, 212, 255, 0.12)",
              border: "1px solid rgba(0, 212, 255, 0.4)",
              color: "var(--accent)",
              fontFamily: "var(--font-mono)",
              fontSize: "0.68rem",
              padding: "3px 10px",
              borderRadius: 20,
              cursor: "pointer",
              pointerEvents: "auto",
              boxShadow: "0 0 12px rgba(0, 212, 255, 0.2)",
            }}
          >
            <span>🗺️</span> SWITCH TO 2D SAR STUDIO
          </button>
        )}
      </div>

      {/* ── 2. ACTIVE STYLE INDICATOR (Top Right) ── */}
      <div id="style-indicator">
        <span className="indicator-label">ACTIVE STYLE</span>
        <span className="indicator-value" id="active-style-name">
          {activeStyle.toUpperCase()}
        </span>
      </div>

      {/* ── 3. TOP-CENTER GLOBE ACTIONS ── */}
      <nav id="top-center-actions" aria-label="Globe actions">
        <button
          id="clear-selected-layers"
          type="button"
          onClick={clearAllLayers}
          title="Turn off all selected data layers"
        >
          <span className="material-symbols-outlined">layers_clear</span>
        </button>
        <button
          id="share-btn"
          type="button"
          onClick={() => navigator.clipboard.writeText(window.location.href)}
          title="Copy share link"
        >
          <span className="share-icon">🔗</span>
        </button>
        <button
          id="tilt-map-view"
          type="button"
          onClick={toggleTilt}
          title="Toggle straight-down and tilted map views"
        >
          <span className="material-symbols-outlined">view_in_ar</span>
        </button>
        <button
          id="north-up-view"
          type="button"
          onClick={resetNorth}
          title="Reset map bearing to north"
        >
          <span className="camera-compass-n">N</span>
          <span className="camera-compass-needle material-symbols-outlined">navigation</span>
        </button>
        <button
          id="reset-globe-view"
          type="button"
          onClick={resetGlobe}
          title="Reset camera and return to full globe view"
        >
          <span className="material-symbols-outlined">public</span>
        </button>
      </nav>

      {/* ── 4. LEFT PANEL STACK (DATA LAYERS, CCTV, WEATHER, RADIO) ── */}
      <div id="left-panel-stack">
        {/* DATA LAYERS PANEL */}
        <div
          id="data-panel"
          className={`panel-collapsible ${dataPanelCollapsed ? "collapsed" : "active"}`}
          data-panel-id="data-panel"
        >
          <div className="panel-glow"></div>
          <div className="data-panel-inner">
            <div className="panel-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span className="panel-title">DATA LAYERS</span>
              <span className="panel-divider"></span>
              <button
                className="panel-collapse-btn"
                onClick={() => setDataPanelCollapsed(!dataPanelCollapsed)}
                title="Collapse panel"
              >
                {dataPanelCollapsed ? "+" : "−"}
              </button>
            </div>

            {!dataPanelCollapsed && (
              <div id="data-toggles" className="data-toggle-list">
                {/* 1. MOVEMENT GROUP */}
                <div className="data-layer-group-heading">Movement</div>
                {[
                  { id: "satellites", label: "Satellites", icon: "🛰️", count: roster.satellites },
                  { id: "aircraft", label: "Commercial Flights", icon: "✈️", count: roster.aircraft },
                  { id: "military", label: "Military Air", icon: "🎖️", count: roster.military, color: "#ff0055" },
                  { id: "vessels", label: "AIS Vessels", icon: "🚢", count: roster.vessels },
                  { id: "transit", label: "Transit Vehicles", icon: "🚊", count: roster.transit },
                  { id: "launches", label: "Space Launches", icon: "🚀", count: roster.launches },
                ].map((item) => (
                  <div key={item.id} className="data-toggle-row" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span>{item.icon}</span>
                      <span style={{ color: (item as any).color || "var(--text-primary)", fontSize: "0.74rem", fontFamily: "var(--font-mono)" }}>
                        {item.label}
                      </span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: "0.68rem", color: "var(--accent)", fontFamily: "var(--font-mono)" }}>
                        {item.count}
                      </span>
                      <input
                        type="checkbox"
                        checked={(layers as any)[item.id]}
                        onChange={(e) => setLayers((l) => ({ ...l, [item.id]: e.target.checked }))}
                        style={{ accentColor: "var(--accent)", cursor: "pointer" }}
                      />
                    </div>
                  </div>
                ))}

                {/* 2. INFRASTRUCTURE GROUP */}
                <div className="data-layer-group-heading">Infrastructure & Defense</div>
                {[
                  { id: "cables", label: "Submarine Cables", icon: "🌐", count: roster.cables },
                  { id: "installations", label: "Defense Bases", icon: "🏰", count: roster.installations },
                  { id: "gnss", label: "GPS Jamming / EW", icon: "⚠️", count: roster.gnss, color: "#ff0055" },
                  { id: "perimeters", label: "ADIZ Perimeters", icon: "🛑", count: roster.perimeters },
                  { id: "radio", label: "WebSDR Radio", icon: "📻", count: roster.radio },
                ].map((item) => (
                  <div key={item.id} className="data-toggle-row" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span>{item.icon}</span>
                      <span style={{ color: (item as any).color || "var(--text-primary)", fontSize: "0.74rem", fontFamily: "var(--font-mono)" }}>
                        {item.label}
                      </span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: "0.68rem", color: "var(--accent)", fontFamily: "var(--font-mono)" }}>
                        {item.count}
                      </span>
                      <input
                        type="checkbox"
                        checked={(layers as any)[item.id]}
                        onChange={(e) => setLayers((l) => ({ ...l, [item.id]: e.target.checked }))}
                        style={{ accentColor: "var(--accent)", cursor: "pointer" }}
                      />
                    </div>
                  </div>
                ))}

                {/* 3. NATURAL HAZARDS GROUP */}
                <div className="data-layer-group-heading">Natural Hazards & Climate</div>
                {[
                  { id: "earthquakes", label: "USGS Earthquakes", icon: "🌋", count: roster.earthquakes },
                  { id: "firms", label: "NASA FIRMS Fires", icon: "🔥", count: roster.firms, color: "#ff6600" },
                  { id: "cyclones", label: "Storms & Cyclones", icon: "🌀", count: roster.cyclones },
                  { id: "weather", label: "Doppler Radar WMS", icon: "🌧️", count: "Live" },
                  { id: "airquality", label: "Air Quality AQI", icon: "🍃", count: roster.airquality },
                ].map((item) => (
                  <div key={item.id} className="data-toggle-row" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span>{item.icon}</span>
                      <span style={{ color: (item as any).color || "var(--text-primary)", fontSize: "0.74rem", fontFamily: "var(--font-mono)" }}>
                        {item.label}
                      </span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: "0.68rem", color: "var(--accent)", fontFamily: "var(--font-mono)" }}>
                        {item.count}
                      </span>
                      <input
                        type="checkbox"
                        checked={(layers as any)[item.id]}
                        onChange={(e) => setLayers((l) => ({ ...l, [item.id]: e.target.checked }))}
                        style={{ accentColor: "var(--accent)", cursor: "pointer" }}
                      />
                    </div>
                  </div>
                ))}

                {/* 4. SENSORS & RECON GROUP */}
                <div className="data-layer-group-heading">Sensors & Reconnaissance</div>
                {[
                  { id: "cctv", label: "Traffic CCTV Network", icon: "📹", count: "Live" },
                  { id: "aois", label: "Sentinel-2 AOIs", icon: "🗺️", count: aois.length },
                ].map((item) => (
                  <div key={item.id} className="data-toggle-row" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span>{item.icon}</span>
                      <span style={{ color: "var(--text-primary)", fontSize: "0.74rem", fontFamily: "var(--font-mono)" }}>
                        {item.label}
                      </span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: "0.68rem", color: "var(--accent)", fontFamily: "var(--font-mono)" }}>
                        {item.count}
                      </span>
                      <input
                        type="checkbox"
                        checked={(layers as any)[item.id]}
                        onChange={(e) => setLayers((l) => ({ ...l, [item.id]: e.target.checked }))}
                        style={{ accentColor: "var(--accent)", cursor: "pointer" }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* CCTV PANEL */}
        <div id="cctv-panel" className={`panel-collapsible ${cctvPanelCollapsed ? "collapsed" : ""}`} data-panel-id="cctv-panel">
          <div className="panel-glow"></div>
          <div className="cctv-panel-inner">
            <div className="panel-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span className="panel-title">CCTV</span>
              <span className="panel-divider"></span>
              <button className="panel-collapse-btn" onClick={() => setCctvPanelCollapsed(!cctvPanelCollapsed)} title="Collapse panel">+</button>
            </div>
            {!cctvPanelCollapsed && (
              <div className="cyber-panel-body" style={{ padding: "8px 0" }}>
                <div id="cctv-frame-wrap" className="cctv-frame-wrap">
                  {activeCctv ? (
                    <img id="cctv-frame" src={`/api/live/cctv/frame?url=${encodeURIComponent(activeCctv.imageUrl)}`} alt="CCTV" />
                  ) : (
                    <span className="cctv-frame-caption">SELECT CAMERA ON GLOBE</span>
                  )}
                </div>
                <div id="cctv-source-badge" style={{ fontSize: "0.68rem", color: "var(--accent)", marginTop: 6 }}>
                  {activeCctv ? `CAMERA: ${activeCctv.name}` : "SOURCE • AUSTIN/TFL TRAFFIC"}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* WEATHER PANEL */}
        <div id="weather-panel" className={`panel-collapsible ${weatherPanelCollapsed ? "collapsed" : ""}`} data-panel-id="weather-panel">
          <div className="panel-glow"></div>
          <div className="weather-panel-inner">
            <div className="panel-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span className="panel-title">WEATHER</span>
              <span className="panel-divider"></span>
              <button className="panel-collapse-btn" onClick={() => setWeatherPanelCollapsed(!weatherPanelCollapsed)} title="Collapse panel">+</button>
            </div>
            {!weatherPanelCollapsed && (
              <div style={{ padding: "8px 4px", fontSize: "0.72rem", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
                <div>🌧️ RainViewer Global Radar: <strong style={{ color: "var(--accent)" }}>ACTIVE</strong></div>
                <div>🌀 Cyclones & Depressions: <strong style={{ color: "#ffaa00" }}>{roster.cyclones} TRACKS</strong></div>
                <div>📡 Atmospheric Sensor: <strong style={{ color: "var(--text-primary)" }}>NOAA / NHC NRT</strong></div>
              </div>
            )}
          </div>
        </div>

        {/* RADIO PANEL */}
        <div id="radio-panel" className={`panel-collapsible ${radioPanelCollapsed ? "collapsed" : ""}`} data-panel-id="radio-panel">
          <div className="panel-glow"></div>
          <div className="radio-panel-inner">
            <div className="panel-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span className="panel-title">RADIO</span>
              <span className="panel-divider"></span>
              <button className="panel-collapse-btn" onClick={() => setRadioPanelCollapsed(!radioPanelCollapsed)} title="Collapse panel">+</button>
            </div>
            {!radioPanelCollapsed && (
              <div style={{ padding: "8px 4px", fontSize: "0.72rem", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
                <div>📻 WebSDR Airband Monitors: <strong style={{ color: "var(--accent)" }}>{roster.radio} ONLINE</strong></div>
                <div>🎧 Channel 16 VHF Marine & Tower ATC: <strong style={{ color: "#00ff9d" }}>STREAMING</strong></div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── 5. RIGHT RAIL (DISPLAY & POST-PROCESSING TOGGLES) ── */}
      <div
        id="pp-toggles"
        className={`panel-collapsible ${ppTogglesCollapsed ? "collapsed" : ""}`}
        data-panel-id="pp-toggles"
        style={{
          position: "fixed",
          top: "12vh",
          right: "36px",
          zIndex: 100,
          width: ppTogglesCollapsed ? "auto" : 260,
        }}
      >
        <div className="compact pp-header-row" style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 12px", background: "var(--glass-bg)", borderRadius: 10, border: "1px solid var(--glass-border)", cursor: "pointer" }} onClick={() => setPpTogglesCollapsed(!ppTogglesCollapsed)}>
          <span className="pp-header-label" style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--text-secondary)", letterSpacing: 2 }}>
            DISPLAY
          </span>
          <span className="panel-divider"></span>
          <button className="panel-collapse-btn pp-collapse-btn" style={{ background: "none", border: "none", color: "var(--accent)", cursor: "pointer" }}>
            {ppTogglesCollapsed ? "◀" : "▶"}
          </button>
        </div>

        {!ppTogglesCollapsed && (
          <div className="pp-panel-body" style={{ background: "var(--glass-bg)", border: "1px solid var(--glass-border)", borderRadius: 12, padding: "12px 14px", marginTop: 6, backdropFilter: "blur(20px)" }}>
            <div className="pp-toggle-group" style={{ marginBottom: 12 }}>
              <button
                className={`pp-toggle-btn ${hudEnabled ? "active" : ""}`}
                id="hud-toggle"
                onClick={() => setHudEnabled(!hudEnabled)}
                style={{ width: "100%", padding: "6px", display: "flex", alignItems: "center", justifyContent: "center", gap: 6, background: hudEnabled ? "rgba(0, 212, 255, 0.2)" : "rgba(255, 255, 255, 0.05)", border: "1px solid var(--accent)", color: "#fff", borderRadius: 6, cursor: "pointer", fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}
              >
                <span className="pp-icon">◎</span>
                <span className="pp-label">HUD OVERLAY</span>
              </button>

              <div className="pp-slider-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
                <span style={{ fontSize: "0.68rem", color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}>Layout</span>
                <select
                  id="hud-layout-select"
                  value={hudLayout}
                  onChange={(e) => setHudLayout(e.target.value as any)}
                  style={{ background: "#0e111a", border: "1px solid var(--glass-border)", color: "var(--accent)", fontFamily: "var(--font-mono)", fontSize: "0.68rem", padding: "2px 6px", borderRadius: 4 }}
                >
                  <option value="tactical">Tactical</option>
                  <option value="operator">Operator</option>
                  <option value="minimal">Minimal</option>
                  <option value="cyber">Cyber</option>
                </select>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10 }}>
                <span style={{ fontSize: "0.68rem", color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}>Cyber Sonar</span>
                <button
                  className={`pp-mode-btn ${sonarActive ? "active" : ""}`}
                  onClick={() => setSonarActive(!sonarActive)}
                  style={{ background: sonarActive ? "var(--accent)" : "#222", border: "none", color: sonarActive ? "#000" : "#888", fontSize: "0.62rem", padding: "2px 8px", borderRadius: 4, cursor: "pointer", fontWeight: 700 }}
                >
                  {sonarActive ? "ON" : "OFF"}
                </button>
              </div>

              {sonarActive && (
                <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 4 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.62rem", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
                    <span>Rings</span>
                    <span>{sonarRings}</span>
                  </div>
                  <input type="range" min="3" max="12" value={sonarRings} onChange={(e) => setSonarRings(Number(e.target.value))} style={{ accentColor: "var(--accent)" }} />

                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.62rem", color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
                    <span>Power</span>
                    <span>{sonarPower}%</span>
                  </div>
                  <input type="range" min="0" max="100" value={sonarPower} onChange={(e) => setSonarPower(Number(e.target.value))} style={{ accentColor: "var(--accent)" }} />
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── 6. COCKPIT ENTRY BUTTON (Bottom Right) ── */}
      <button
        id="cockpit-entry"
        type="button"
        onClick={() => setCockpitActive(!cockpitActive)}
        title="Toggle Jet Fighter Cockpit View (C)"
      >
        <span className="material-symbols-outlined">flight</span>
        <span>{cockpitActive ? "EXIT COCKPIT" : "COCKPIT"}</span>
        <kbd>C</kbd>
      </button>

      {/* ── 7. JET FIGHTER COCKPIT HUD OVERLAY (When Active) ── */}
      {cockpitActive && (
        <section id="cockpit-hud" aria-label="Aircraft cockpit view" style={{ display: "block" }}>
          <svg className="cockpit-frame-lines" viewBox="0 0 1200 720" preserveAspectRatio="none" aria-hidden="true">
            <g fill="none" stroke="currentColor">
              <path d="M42 106H234L266 126H334 M866 126H934L966 106H1158 M42 114H226L258 136H318 M882 136H942L974 114H1158" />
              <path d="M42 616H226L254 598H320 M880 598H946L974 616H1158 M42 624H238L266 606H330 M870 606H934L962 624H1158" />
              <path d="M322 650H878L858 622H728L708 634H492L472 622H342Z M348 659H852" />
            </g>
          </svg>

          {/* Center Target Hairline */}
          <div className="cockpit-scan-array">
            <svg className="cockpit-target-geometry" viewBox="0 0 600 600" fill="none">
              <g className="cockpit-target-hairline" stroke="var(--cockpit-accent, #00d4ff)" strokeWidth="1.5">
                <circle cx="300" cy="300" r="240" strokeOpacity="0.4" />
                <circle cx="300" cy="300" r="140" strokeDasharray="4 8" strokeOpacity="0.6" />
                <path d="M220 300H260 M340 300H380 M300 220V260 M300 340V380" />
              </g>
            </svg>
          </div>

          {/* Visor Shell Pitch & Horizon */}
          <div className="cockpit-visor-shell">
            <div className="cockpit-roll-arc">
              <span className="active">HDG {hudCoords.heading}°</span>
            </div>
            <div className="cockpit-pitch-rail cockpit-pitch-rail-left">
              <span>+20</span>
              <span>+10</span>
              <span className="active">PITCH {hudCoords.pitch}°</span>
              <span>−10</span>
              <span>−20</span>
            </div>
            <div className="cockpit-pitch-rail cockpit-pitch-rail-right">
              <span>ALT {(hudCoords.alt / 1000).toFixed(1)} km</span>
            </div>
            <div className="cockpit-horizon-guide">
              <span></span>
              <small>HORIZON</small>
              <span></span>
            </div>
          </div>
        </section>
      )}

      {/* ── 8. UNIFIED COMMAND DOCK (Bottom Center) ── */}
      <div id="command-dock">
        {/* Left Tray: LOCATION BAR */}
        <div id="location-bar" className={`panel-collapsible ${locationExpanded ? "" : "collapsed"}`}>
          <div className="panel-glow"></div>
          <div className="location-inner">
            <div className="location-toolbar">
              <button
                id="location-bar-toggle"
                className="dock-tray-toggle"
                type="button"
                onClick={() => setLocationExpanded(!locationExpanded)}
              >
                <span className="location-toolbar-label">
                  <span className="dock-label-icon dock-label-icon-location"></span>LOCATION
                </span>
              </button>
              <button
                className="panel-collapse-btn"
                onClick={() => setLocationExpanded(!locationExpanded)}
              >
                {locationExpanded ? "−" : "+"}
              </button>
            </div>

            {!locationExpanded && (
              <div id="location-mini-status" className="location-mini-status" style={{ display: "grid" }}>
                <div id="location-mini-city" className="location-mini-city">
                  📍 {activeLocation}
                </div>
              </div>
            )}

            {locationExpanded && (
              <div id="location-bar-popover" className="dock-popover-content">
                <div className="location-city-row" style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "8px 0" }}>
                  <div id="location-pills" className="location-pills" style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {STRATEGIC_LOCATIONS.map((loc) => (
                      <button
                        key={loc.name}
                        onClick={() => {
                          setActiveLocation(loc.name);
                          flyTo(loc.lon, loc.lat, loc.alt, loc.pitch);
                        }}
                        style={{
                          background: activeLocation === loc.name ? "rgba(0, 212, 255, 0.25)" : "rgba(255, 255, 255, 0.05)",
                          border: activeLocation === loc.name ? "1px solid var(--accent)" : "1px solid var(--glass-border)",
                          color: activeLocation === loc.name ? "#fff" : "var(--text-secondary)",
                          fontFamily: "var(--font-mono)",
                          fontSize: "0.68rem",
                          padding: "3px 8px",
                          borderRadius: 6,
                          cursor: "pointer",
                        }}
                      >
                        {loc.name}
                      </button>
                    ))}
                  </div>

                  <div className="location-search-wrap" style={{ display: "flex", gap: 4, width: "100%", marginTop: 6 }}>
                    <input
                      type="text"
                      id="location-search"
                      placeholder="Search any location..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && searchQuery) {
                          setActiveLocation(searchQuery);
                        }
                      }}
                      style={{
                        flex: 1,
                        background: "#080c14",
                        border: "1px solid var(--glass-border)",
                        color: "#fff",
                        fontFamily: "var(--font-mono)",
                        fontSize: "0.72rem",
                        padding: "6px 10px",
                        borderRadius: 6,
                      }}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Center: Live Telemetry Status Readout */}
        <div id="gev-voice-control" style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "0 14px", fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--accent)" }}>
          <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "var(--accent)", marginRight: 6, boxShadow: "0 0 8px var(--accent-glow)" }}></span>
          <span>{hudCoords.lat.toFixed(2)}°, {hudCoords.lon.toFixed(2)}° • {hudCoords.alt >= 1000 ? `${(hudCoords.alt / 1000).toFixed(0)} km` : `${hudCoords.alt} m`}</span>
        </div>

        {/* Right Tray: VISUAL PRESETS & MAP SOURCE */}
        <div id="control-panel" className={`panel-collapsible ${presetsExpanded ? "" : "collapsed"}`}>
          <div className="panel-glow"></div>
          <div className="panel-inner">
            <button
              id="control-panel-toggle"
              className="panel-header dock-tray-toggle"
              type="button"
              onClick={() => setPresetsExpanded(!presetsExpanded)}
            >
              <span className="panel-title">
                <span className="dock-label-icon dock-label-icon-presets"></span>VISUAL PRESETS
              </span>
              <span className="panel-divider"></span>
            </button>

            {!presetsExpanded && (
              <div id="style-mini-status" className="panel-mini-status" style={{ display: "flex" }}>
                <span className="panel-mini-label">Style</span>
                <span id="style-mini-value" className="panel-mini-value">
                  {activeStyle.toUpperCase()}
                </span>
              </div>
            )}

            {presetsExpanded && (
              <div id="control-panel-popover" className="dock-popover-content">
                <div id="style-buttons" className="button-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 6, padding: "8px 0" }}>
                  {[
                    { id: "normal", label: "Normal", key: "1", icon: "◉" },
                    { id: "retro", label: "CRT", key: "2", icon: "📺" },
                    { id: "surveillance", label: "NVG", key: "3", icon: "🟢" },
                    { id: "thermal", label: "FLIR", key: "4", icon: "🔥" },
                    { id: "anime", label: "Anime", key: "5", icon: "✨" },
                    { id: "noir", label: "Noir", key: "6", icon: "🎬" },
                    { id: "snow", label: "Snow", key: "7", icon: "❄️" },
                  ].map((s) => (
                    <button
                      key={s.id}
                      className={`style-btn ${activeStyle === s.id ? "active" : ""}`}
                      onClick={() => setActiveStyle(s.id as VisualStyle)}
                      style={{
                        background: activeStyle === s.id ? "rgba(0, 212, 255, 0.25)" : "rgba(255, 255, 255, 0.04)",
                        border: activeStyle === s.id ? "1px solid var(--accent)" : "1px solid var(--glass-border)",
                        color: activeStyle === s.id ? "#fff" : "var(--text-secondary)",
                        fontFamily: "var(--font-mono)",
                        fontSize: "0.68rem",
                        padding: "6px 8px",
                        borderRadius: 6,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                      }}
                    >
                      <span>{s.icon}</span>
                      <span>{s.label}</span>
                      <span style={{ opacity: 0.4, marginLeft: "auto", fontSize: "0.58rem" }}>{s.key}</span>
                    </button>
                  ))}
                </div>

                <section className="map-source-section" style={{ marginTop: 8, borderTop: "1px solid var(--glass-border)", paddingTop: 8 }}>
                  <div className="map-source-heading" style={{ display: "flex", justifyContent: "space-between", fontSize: "0.65rem", color: "var(--text-dim)", fontFamily: "var(--font-mono)", marginBottom: 4 }}>
                    <span>MAP SOURCE</span>
                    <span id="map-stack-status" className="pp-stack-status" style={{ color: "var(--accent)" }}>{activeMapSource.toUpperCase()}</span>
                  </div>
                  <div id="map-stack-chips" className="map-stack-chip-row" style={{ display: "flex", gap: 4 }}>
                    {[
                      { id: "3d", label: "3D Photorealistic" },
                      { id: "esri", label: "Satellite (Esri)" },
                      { id: "osm", label: "OpenStreetMap" },
                    ].map((m) => (
                      <button
                        key={m.id}
                        onClick={() => setActiveMapSource(m.id as any)}
                        style={{
                          background: activeMapSource === m.id ? "rgba(0, 212, 255, 0.2)" : "rgba(255, 255, 255, 0.04)",
                          border: activeMapSource === m.id ? "1px solid var(--accent)" : "1px solid var(--glass-border)",
                          color: activeMapSource === m.id ? "#fff" : "var(--text-secondary)",
                          fontSize: "0.62rem",
                          fontFamily: "var(--font-mono)",
                          padding: "3px 8px",
                          borderRadius: 4,
                          cursor: "pointer",
                        }}
                      >
                        {m.label}
                      </button>
                    ))}
                  </div>
                </section>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── 9. TARGET CONTEXT INSPECTION CARD ── */}
      {activeInspection && (
        <div
          id="context"
          style={{
            position: "fixed",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            background: "rgba(10, 10, 15, 0.92)",
            border: "1px solid var(--accent)",
            boxShadow: "0 12px 48px rgba(0, 0, 0, 0.8), 0 0 24px rgba(0, 212, 255, 0.25)",
            borderRadius: 12,
            padding: "16px 20px",
            minWidth: 380,
            maxWidth: 520,
            zIndex: 300,
            backdropFilter: "blur(24px)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
            <div>
              <div style={{ fontSize: "0.62rem", color: "var(--accent)", letterSpacing: "1.5px", fontFamily: "var(--font-mono)", fontWeight: 700 }}>
                ◈ {activeInspection.type}
              </div>
              <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#fff", marginTop: 2, fontFamily: "var(--font-mono)" }}>
                {activeInspection.title}
              </div>
              <div style={{ fontSize: "0.74rem", color: "var(--text-secondary)", marginTop: 2 }}>
                {activeInspection.subtitle}
              </div>
            </div>
            <button
              onClick={() => setActiveInspection(null)}
              style={{
                background: "none",
                border: "none",
                color: "var(--text-secondary)",
                fontSize: "1.2rem",
                cursor: "pointer",
              }}
            >
              ✕
            </button>
          </div>

          <div
            style={{
              background: "rgba(0, 0, 0, 0.45)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: 8,
              padding: "10px 14px",
              margin: "10px 0",
            }}
          >
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 16px" }}>
              <div>
                <span style={{ fontSize: "0.62rem", color: "var(--text-dim)", fontFamily: "var(--font-mono)", display: "block" }}>
                  COORDINATES
                </span>
                <span style={{ fontSize: "0.74rem", color: "var(--accent)", fontFamily: "var(--font-mono)" }}>
                  {activeInspection.coordinates[1].toFixed(4)}°, {activeInspection.coordinates[0].toFixed(4)}°
                </span>
              </div>
              {activeInspection.metrics.map((m) => (
                <div key={m.label}>
                  <span style={{ fontSize: "0.62rem", color: "var(--text-dim)", fontFamily: "var(--font-mono)", display: "block" }}>
                    {m.label.toUpperCase()}
                  </span>
                  <span style={{ fontSize: "0.74rem", color: "#fff", fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                    {m.value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 12 }}>
            <button
              onClick={() => flyTo(activeInspection.coordinates[0], activeInspection.coordinates[1], 150_000, -55)}
              style={{
                background: "rgba(0, 212, 255, 0.2)",
                border: "1px solid var(--accent)",
                color: "var(--accent)",
                fontFamily: "var(--font-mono)",
                fontSize: "0.72rem",
                padding: "6px 14px",
                borderRadius: 6,
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              🎯 LOCK CAMERA & ZOOM
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
