import { artifactUrl } from "../api/client";
import type { ExplainabilityArtifact } from "../api/types";

interface ExplainabilityGalleryProps {
  aoiId: string;
  artifacts: ExplainabilityArtifact[];
}

export default function ExplainabilityGallery({
  aoiId,
  artifacts,
}: ExplainabilityGalleryProps) {
  const heatmaps = artifacts.filter((a) => a.type === "heatmap");
  const beforeAfter = artifacts.filter((a) => a.type === "before_after");

  if (heatmaps.length === 0 && beforeAfter.length === 0) {
    return (
      <section className="panel gallery-panel">
        <header className="panel-header">
          <h2>Visuals</h2>
        </header>
        <p className="panel-empty">No heatmaps or comparisons in this run.</p>
      </section>
    );
  }

  return (
    <section className="panel gallery-panel">
      <header className="panel-header">
        <h2>Visuals</h2>
      </header>

      {heatmaps.length > 0 && (
        <div className="gallery-grid">
          {heatmaps.map((art) => (
            <figure key={art.path} className="gallery-figure">
              <img
                src={artifactUrl(aoiId, art.path)}
                alt={art.description || art.name}
                loading="lazy"
              />
              <figcaption>{art.name}</figcaption>
            </figure>
          ))}
        </div>
      )}

      {beforeAfter.length > 0 && (
        <div className="gallery-grid before-after">
          {beforeAfter.map((art) => (
            <figure key={art.path} className="gallery-figure wide">
              <img
                src={artifactUrl(aoiId, art.path)}
                alt={art.description || art.name}
                loading="lazy"
              />
              <figcaption>{art.description || art.name}</figcaption>
            </figure>
          ))}
        </div>
      )}
    </section>
  );
}
