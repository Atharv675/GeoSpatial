# Brag Plan: GeoSentinel

## What is this app?
GeoSentinel is a deterministic geospatial intelligence and OSINT fusion platform that combines Sentinel-1 SAR, Sentinel-2 optical imagery, and live open-source feeds (GDELT, FIRMS, ACLED) for explainable temporal anomaly detection.

## The angle
Mission-critical situational awareness without black-box ML hallucinations: orbital radar and optical satellites fused with ground truth in a unified analyst dashboard.

## Hook (first 2-3 seconds)
Deep space radar sweep and coordinate targeting: "From orbit, the world is changing. Most systems guess. GeoSentinel verifies."

## Key moments (the middle)
- **Multi-Sensor Satellite Ingestion**: Sentinel-1 SAR all-weather radar meets Sentinel-2 optical multispectral change analysis.
- **Real Satellite Anomaly Detection**: Actual before/after NDVI difference and optical spectral shifts detected across AOIs.
- **Tri-Source OSINT Ground Correlation**: Instant rule-based verification against FIRMS thermal hotspots (FRP=42.1), ACLED incident reports, and GDELT news streams.
- **Operational Explainability**: Transparent confidence breakdowns and chronological audit timelines.

## Outro / punchline
"GeoSentinel. Orbital Intelligence. Ground Truth. Zero Guesswork."

## User flow worth showing
1. **Target Selection**: Analyst selects AOI (`aoi-levant` / `aoi-delta`).
2. **Automated Fusion Run**: Pipeline cross-references SAR backscatter with optical NDVI and OSINT triggers.
3. **Critical Alert & Evidence**: System flags `CRITICAL — aoi-levant` with composite score 1.00 and visual before/after proof.

## Tone
- Preset: `cinematic`
- Creative direction: Mission-critical defense-tech intelligence briefing
- Interpretation: Crisp, high-contrast, confident military-grade precision with sleek animations, tactical telemetry, and zero fluff.

## Format: landscape — 1920x1080
## Duration: 20s

## Visual identity (from the project)
- Background: `#0f1419` (Tactical deep slate)
- Surface: `#1a2332` (Radar console navy)
- Accent: `#3d8bfd` (Satellite telemetry cyan-blue)
- Critical / Danger: `#e85d4c` (Incident red)
- Warning / Heat: `#f0ad4e` (Thermal amber)
- OK / Verified: `#5bc0be` (Signal emerald)
- Text: `#e7ecf3` (High-contrast frost white)
- Muted: `#8b9cb3` (Console gray)
- Display font: `Inter, system-ui, sans-serif`
- Body font: `JetBrains Mono, monospace` (for telemetry, coordinates, and scores)
- Strongest visual element: Real before-and-after satellite NDVI comparison, telemetry grid, and live critical alert badge.

## Share copy (draft)
Detect temporal anomalies from orbit before ground reports break. Meet GeoSentinel — Sentinel SAR/Optical fusion meets explainable OSINT.

## Audio direction
- Role: Cinematic electronic support with tactical data accents
- Music: `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3`
- Music treatment: High-energy tech groove starting immediately, building through satellite detection, peaking at critical alert reveal, fading smoothly at logo outro.
- SFX posture: Crisp motion-matched UI accents: radar blip, high-tech confirmation click, alarm pulse on critical alert, smooth whoosh on scene transitions.
- Restraint rule: Never obscure text; no cartoon sound effects.

## Storyboard

### Scene 1 — The Hook (Orbital Surveillance) — 3.0s (0.0s - 3.0s)
- **Visual**: Satellite telemetry overlay, reticle sweeping over coordinates (34.5° N, 36.2° E), pulsing radar grid.
- **Copy**: "THE PLANET IS CHANGING." / "MOST PLATFORMS GUESS. GEOSENTINEL VERIFIES."
- **Audio intent**: Suspenseful tech swell, low radar ping.

### Scene 2 — Multi-Sensor Fusion — 4.5s (3.0s - 7.5s)
- **Visual**: Twin orbital sensor cards slide in: "Sentinel-1 SAR (Radar)" + "Sentinel-2 L2A (Optical NDVI)".
- **Copy**: "Deterministic Temporal Anomaly Detection" / "All-Weather Satellite Monitoring"
- **Audio intent**: Upbeat synth groove drops in, data click sounds.

### Scene 3 — Real Satellite Anomaly & Evidence — 6.0s (7.5s - 13.5s)
- **Visual**: Real satellite before/after imagery with NDVI difference slider. Flashing tactical alert badge: `CRITICAL — aoi-levant`. Scores count up: Geospatial 1.00 | OSINT 0.80.
- **Copy**: "CRITICAL ANOMALY DETECTED" / "ACLED (Unrest) + FIRMS (Thermal Hotspots) + GDELT"
- **Audio intent**: Tactical alert pulse, rapid counter tick, peak musical momentum.

### Scene 4 — Operational Explainability — 4.0s (13.5s - 17.5s)
- **Visual**: Explainability matrix and chronological event timeline. Complete audit trail with zero black-box hallucination.
- **Copy**: "100% EXPLAINABLE" / "Audit-grade evidence for regional situational awareness"
- **Audio intent**: Confident rhythm, clean sweep.

### Scene 5 — Outro & Punchline — 2.5s (17.5s - 20.0s)
- **Visual**: GeoSentinel central emblem, glowing cyan ring, tagline, and tech stack badges (FastAPI · React · PostGIS · Leaflet).
- **Copy**: "GeoSentinel" / "Orbital Intelligence. Ground Truth. Zero Guesswork."
- **Audio intent**: Final punch, music tail fading out smoothly.

**Music mood for this video:** High-tech cinematic electronic
**Audio summary:** Focused tactical intelligence briefing that builds momentum from orbit to ground-truth confirmation.
