import type { LayerVisibility } from "../overlays/MapOverlays";

interface LayerControlsProps {
  layers: LayerVisibility;
  onChange: (layers: LayerVisibility) => void;
  hasBoundary: boolean;
  hasAnomaly: boolean;
  hasOsint: boolean;
}

export default function LayerControls({
  layers,
  onChange,
  hasBoundary,
  hasAnomaly,
  hasOsint,
}: LayerControlsProps) {
  const toggle = (key: keyof LayerVisibility) => {
    onChange({ ...layers, [key]: !layers[key] });
  };

  return (
    <fieldset className="layer-controls">
      <legend>Map layers</legend>
      <label>
        <input
          type="checkbox"
          checked={layers.boundary}
          disabled={!hasBoundary}
          onChange={() => toggle("boundary")}
        />
        AOI boundary
      </label>
      <label>
        <input
          type="checkbox"
          checked={layers.anomaly}
          disabled={!hasAnomaly}
          onChange={() => toggle("anomaly")}
        />
        Anomaly summary
      </label>
      <label>
        <input
          type="checkbox"
          checked={layers.osint}
          disabled={!hasOsint}
          onChange={() => toggle("osint")}
        />
        OSINT markers
      </label>
    </fieldset>
  );
}
