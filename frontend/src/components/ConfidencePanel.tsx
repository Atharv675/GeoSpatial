import type { ConfidenceBreakdown, OperationalAlert } from "../api/types";
import StatusBadge from "./StatusBadge";

interface ConfidencePanelProps {
  breakdown: ConfidenceBreakdown | null;
  alert: OperationalAlert | null;
  loading?: boolean;
}

export default function ConfidencePanel({
  breakdown,
  alert,
  loading,
}: ConfidencePanelProps) {
  if (loading) {
    return (
      <section className="panel confidence-panel">
        <header className="panel-header">
          <h2>Confidence</h2>
        </header>
        <p className="panel-empty">Loading…</p>
      </section>
    );
  }

  if (!breakdown) {
    return (
      <section className="panel confidence-panel">
        <header className="panel-header">
          <h2>Confidence</h2>
        </header>
        <p className="panel-empty">No confidence breakdown available.</p>
      </section>
    );
  }

  const geo = breakdown.geospatial as {
    composite_score?: number;
    is_anomaly?: boolean;
    signals?: { signal: string; triggered?: boolean; value?: number }[];
  };
  const osint = breakdown.osint as {
    fusion_confidence?: number;
    sources_agreeing?: string[];
    top_matches?: { title?: string; confidence?: number; source?: string }[];
  };
  const fusion = breakdown.fusion as { combined_assessment?: string };

  return (
    <section className="panel confidence-panel">
      <header className="panel-header">
        <h2>Confidence</h2>
        {alert && (
          <StatusBadge
            label={alert.severity}
            ok={alert.severity === "low" || alert.severity === "medium"}
          />
        )}
      </header>

      {breakdown.summary && <p className="confidence-summary">{breakdown.summary}</p>}

      {alert && (
        <div className="alert-card">
          <strong>{alert.title}</strong>
          <p>{alert.summary}</p>
        </div>
      )}

      <dl className="confidence-metrics">
        <dt>Geospatial score</dt>
        <dd>{(geo.composite_score ?? 0).toFixed(2)}</dd>
        <dt>Anomaly flagged</dt>
        <dd>{geo.is_anomaly ? "Yes" : "No"}</dd>
        <dt>OSINT fusion</dt>
        <dd>{(osint.fusion_confidence ?? 0).toFixed(2)}</dd>
        {osint.sources_agreeing && osint.sources_agreeing.length > 0 && (
          <>
            <dt>Sources agreeing</dt>
            <dd>{osint.sources_agreeing.join(", ")}</dd>
          </>
        )}
      </dl>

      {fusion.combined_assessment && (
        <p className="fusion-assessment">
          <strong>Assessment:</strong> {fusion.combined_assessment}
        </p>
      )}

      {geo.signals && geo.signals.length > 0 && (
        <div className="signals-block">
          <h3>Triggered signals</h3>
          <ul>
            {geo.signals
              .filter((s) => s.triggered)
              .map((s) => (
                <li key={s.signal}>
                  {s.signal} ({(s.value ?? 0).toFixed(2)})
                </li>
              ))}
          </ul>
        </div>
      )}

      {osint.top_matches && osint.top_matches.length > 0 && (
        <div className="matches-block">
          <h3>Top OSINT matches</h3>
          <ul>
            {osint.top_matches.map((m, i) => (
              <li key={i}>
                {m.title ?? "Event"} — {m.source} ({(m.confidence ?? 0).toFixed(2)})
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
