import React, { useState, useMemo } from "react";
import { Button } from "../../../components";
import { RunEventRecord } from "../../runs/types";

export interface EventConsoleProps {
  events: RunEventRecord[];
  isLive: boolean;
  onRefresh: () => void;
  runId?: string;
  onDownloadDebugBundle?: () => void;
}

export const EventConsole: React.FC<EventConsoleProps> = ({
  events,
  isLive,
  onRefresh,
  runId = "",
  onDownloadDebugBundle,
}) => {
  const [clearedEventIds, setClearedEventIds] = useState<Set<string>>(new Set());
  const [eventLevelFilter, setEventLevelFilter] = useState<string>("all");
  const [eventSearch, setEventSearch] = useState<string>("");
  const [expandedEventIds, setExpandedEventIds] = useState<Set<string>>(new Set());

  const isCleared = events.length > 0 && clearedEventIds.size > 0 && events.every((e) => clearedEventIds.has(e.event_id));

  const handleClearConsole = () => {
    if (isCleared) {
      setClearedEventIds(new Set());
    } else {
      setClearedEventIds(new Set(events.map((e) => e.event_id)));
    }
  };

  const handleToggleExpandEvent = (id: string) => {
    setExpandedEventIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const visibleEvents = useMemo(() => {
    return events.filter((e) => {
      if (clearedEventIds.has(e.event_id)) return false;
      if (eventLevelFilter !== "all" && e.level.toLowerCase() !== eventLevelFilter.toLowerCase()) return false;
      if (eventSearch.trim()) {
        const q = eventSearch.trim().toLowerCase();
        const text = `${e.operation} ${e.message} ${e.stage_id || ""}`.toLowerCase();
        if (!text.includes(q)) return false;
      }
      return true;
    });
  }, [events, clearedEventIds, eventLevelFilter, eventSearch]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="console-toolbar">
        {isCleared ? (
          <p>Current view cleared. Backend evidence remains available.</p>
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            {isLive && (
              <span
                style={{
                  fontSize: 11,
                  background: "var(--info-soft)",
                  color: "var(--info)",
                  padding: "2px 6px",
                  borderRadius: "var(--radius-pill)",
                  fontWeight: 600,
                }}
              >
                ● Live Streaming
              </span>
            )}
            <label htmlFor="eventLevelFilter" style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
              Event level:
            </label>
            <select
              id="eventLevelFilter"
              value={eventLevelFilter}
              onChange={(e) => setEventLevelFilter(e.target.value)}
              className="field"
              style={{ fontSize: 12, padding: "4px 8px", width: "auto", minHeight: 32 }}
              aria-label="Filter events by level"
              title="Event level"
            >
              <option value="all">All event levels</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
            </select>

            <input
              type="search"
              placeholder="Search console..."
              value={eventSearch}
              onChange={(e) => setEventSearch(e.target.value)}
              className="field"
              style={{ fontSize: 12, padding: "4px 8px", width: 160, minHeight: 32 }}
              aria-label="Search console logs"
            />
          </div>
        )}

        <div className="console-actions">
          <Button
            size="compact"
            variant="secondary"
            onClick={handleClearConsole}
          >
            {isCleared ? "Show History" : "Clear View"}
          </Button>

          {onDownloadDebugBundle && (
            <Button
              size="compact"
              variant="secondary"
              onClick={onDownloadDebugBundle}
            >
              Download Debug Bundle
            </Button>
          )}

          <Button
            size="compact"
            variant="secondary"
            onClick={onRefresh}
          >
            Refresh Logs
          </Button>
        </div>
      </div>

      <div
        className="console-log"
        role="log"
        aria-live="polite"
        aria-label={`Console log for ${runId || "run"}`}
        tabIndex={0}
      >
        {visibleEvents.length === 0 ? (
          <div className="console-empty">
            {isCleared ? "Current view cleared. Backend evidence remains available." : "No console events in current view."}
          </div>
        ) : (
          visibleEvents.map((ev) => {
            const isExpanded = expandedEventIds.has(ev.event_id);
            return (
              <div key={ev.event_id} className="console-line">
                <span className="console-time">
                  {new Date(ev.time).toLocaleTimeString()}
                </span>
                <span className="console-level" data-level={ev.level}>
                  {ev.level.toUpperCase()}
                </span>
                <span className="console-operation">
                  {ev.stage_id || ev.operation}
                </span>
                <span className="console-message">
                  {ev.message}
                  {ev.payload && Object.keys(ev.payload).length > 0 && (
                    <>
                      {" "}
                      <button
                        type="button"
                        onClick={() => handleToggleExpandEvent(ev.event_id)}
                        style={{
                          border: "none",
                          background: "transparent",
                          color: "var(--accent)",
                          cursor: "pointer",
                          fontSize: 11,
                          padding: 0,
                          textDecoration: "underline",
                        }}
                      >
                        {isExpanded ? "Hide data" : "Data"}
                      </button>
                    </>
                  )}
                  {isExpanded && ev.payload && (
                    <pre
                      style={{
                        margin: "4px 0 0 0",
                        padding: "6px 8px",
                        background: "#161b22",
                        border: "1px solid #30363d",
                        borderRadius: 4,
                        fontSize: 11,
                        color: "#c9d1d9",
                        overflowX: "auto",
                      }}
                    >
                      {JSON.stringify(ev.payload, null, 2)}
                    </pre>
                  )}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
