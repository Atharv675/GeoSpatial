import { useMemo, useState } from "react";
import type { TimelineEvent } from "../api/types";

interface TimelinePanelProps {
  events: TimelineEvent[];
  runId?: string;
}

type CategoryFilter = "all" | "anomaly" | "signal" | "osint";

export default function TimelinePanel({ events, runId }: TimelinePanelProps) {
  const [filter, setFilter] = useState<CategoryFilter>("all");
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  const filtered = useMemo(() => {
    if (filter === "all") return events;
    return events.filter((e) => e.category === filter);
  }, [events, filter]);

  return (
    <section className="panel timeline-panel">
      <header className="panel-header">
        <h2>Timeline</h2>
        {runId && <span className="panel-meta">run {runId}</span>}
      </header>

      <div className="timeline-filters" role="group" aria-label="Timeline category">
        {(["all", "anomaly", "signal", "osint"] as CategoryFilter[]).map((cat) => (
          <button
            key={cat}
            type="button"
            className={filter === cat ? "chip active" : "chip"}
            onClick={() => {
              setFilter(cat);
              setSelectedIdx(null);
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="panel-empty">No timeline events for this filter.</p>
      ) : (
        <ol className="timeline-list">
          {filtered.map((ev, idx) => (
            <li
              key={`${ev.datetime}-${ev.label}-${idx}`}
              className={selectedIdx === idx ? "timeline-item selected" : "timeline-item"}
            >
              <button
                type="button"
                className="timeline-item-btn"
                onClick={() => setSelectedIdx(selectedIdx === idx ? null : idx)}
              >
                <time dateTime={ev.datetime}>{formatDatetime(ev.datetime)}</time>
                <span className={`timeline-cat cat-${ev.category}`}>{ev.category}</span>
                <span className="timeline-label">{ev.label}</span>
                {ev.score != null && (
                  <span className="timeline-score">{ev.score.toFixed(2)}</span>
                )}
              </button>
              {selectedIdx === idx && ev.source && (
                <p className="timeline-detail">Source: {ev.source}</p>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function formatDatetime(raw: string): string {
  if (!raw) return "—";
  const d = new Date(raw.length === 8 ? `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}` : raw);
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
