# Hyperframes Composition Brief: GeoSentinel

## Objective
Create a short, cinematic launch-style brag video for GeoSentinel.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 20 seconds (600 frames at 30fps)

## Source Material
- Project root: `.`
- Primary files read: `README.md`, `frontend/src/index.css`, `frontend/src/pages/DashboardPage.tsx`, `data/explainability/`, `data/alerts/alerts_state.json`
- Product name: GeoSentinel
- Tagline: Geospatial intelligence & OSINT fusion platform
- Key UI / visual moments to recreate:
  - Coordinate telemetry grid with radar reticle
  - Sentinel-1 SAR & Sentinel-2 Optical sensor telemetry
  - Real before/after satellite imagery (`optical_s2-delta-w1-b04_vs_s2-delta-w1-b08.png`, `ndvi_20260501_vs_20260508.png`)
  - Operational alert badge: `CRITICAL — aoi-levant`
  - Confidence breakdown: Geospatial 1.00, OSINT Fusion 0.80, Correlated feeds (ACLED, FIRMS, GDELT)
- Copy that must appear verbatim:
  - "GeoSentinel"
  - "Geospatial intelligence & OSINT fusion"
  - "CRITICAL — aoi-levant"
  - "Geospatial composite 1.00; OSINT fusion 0.80; 3 correlated events"
  - "Orbital Intelligence. Ground Truth. Zero Guesswork."

## Creative Direction
- Tone preset: cinematic
- Creative direction: Mission-critical defense-tech intelligence briefing
- Interpretation: Deep space darkness with glowing tactical cyan, emerald OK indicators, and vivid incident amber/red. Fluid motion, sharp typography, readable timings.
- Avoid: Generic SaaS buzzwords, cheesy stock illustrations, cartoon transitions.

## Visual Identity
- Background: `#0f1419`
- Surface: `#1a2332`
- Text: `#e7ecf3`
- Accent: `#3d8bfd`
- Danger: `#e85d4c`
- Warn: `#f0ad4e`
- Ok: `#5bc0be`
- Border: `#2a3548`
- Display font: `system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif`
- Monospace font: `'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace`

## Storyboard & Timing (30 fps, 600 frames total)
- Scene 1 (0s - 3s, frames 0 - 90): Orbital surveillance hook & radar reticle.
- Scene 2 (3s - 7.5s, frames 90 - 225): Multi-Sensor Satellite Ingestion (Sentinel-1 SAR + Sentinel-2 Optical).
- Scene 3 (7.5s - 13.5s, frames 225 - 405): Real Satellite Anomaly & Ground OSINT Correlation (Before/After NDVI slider, Critical Alert).
- Scene 4 (13.5s - 17.5s, frames 405 - 525): Operational Explainability & Timeline Audit.
- Scene 5 (17.5s - 20s, frames 525 - 600): GeoSentinel Logo Outro, Tagline & Tech Stack.

## Audio
- Audio role: Cinematic electronic groove with crisp tactical telemetry sound effects.
- Music: `assets/music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3`
- Audio files: Copied into `brag-output/composition/assets/`
