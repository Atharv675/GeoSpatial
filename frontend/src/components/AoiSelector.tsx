import type { AoiFeature } from "../api/types";

interface AoiSelectorProps {
  aois: AoiFeature[];
  selectedId: string | null;
  onSelect: (aoiId: string) => void;
  disabled?: boolean;
}

export default function AoiSelector({
  aois,
  selectedId,
  onSelect,
  disabled,
}: AoiSelectorProps) {
  return (
    <div className="aoi-selector">
      <label htmlFor="aoi-select">Area of interest</label>
      <select
        id="aoi-select"
        value={selectedId ?? ""}
        onChange={(e) => onSelect(e.target.value)}
        disabled={disabled || aois.length === 0}
      >
        {aois.length === 0 ? (
          <option value="">No AOIs configured</option>
        ) : (
          aois.map((f) => (
            <option key={f.properties.aoi_id} value={f.properties.aoi_id}>
              {f.properties.name}
            </option>
          ))
        )}
      </select>
    </div>
  );
}
