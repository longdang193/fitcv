import React, { useState, useRef, useEffect, useMemo } from "react";
import { Button } from "../../../components";
import { RunEventRecord } from "../../runs/types";

export interface EventConsoleProps {
  events: RunEventRecord[];
  isLive: boolean;
  onRefresh: () => void;
}

export const EventConsole: React.FC<EventConsoleProps> = ({
  events,
  isLive,
  onRefresh,
}) => {
  const [clearedEventIds, setClearedEventIds] = useState<Set<string>>(new Set());
  const [eventLevelFilter, setEventLevelFilter] = useState<string>("all");
  const [eventSearch, setEventSearch] = useState<string>("");
  const [autoScroll, setAutoScroll] = useState(false);
  const [expandedEventIds, setExpandedEventIds] = useState<Set<string>>(new Set());
  const consoleBottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // Auto-scroll disabled to prevent disruptive window scrolling on new events
  }, [events]);

  const handleClearConsole = () => {
    setClearedEventIds(new Set(events.map((e) => e.event_id)));
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
      if (eventLevelFilter !== "all" && e.level !== eventLevelFilter) return false;
      if (eventSearch.trim()) {
        const q = eventSearch.trim().toLowerCase();
        const text = `${e.operation} ${e.message} ${e.stage_id}`.toLowerCase();
        if (!text.includes(q)) return false;
      }
      return true;
    });
  }, [events, clearedEventIds, eventLevelFilter, eventSearch]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)",
        padding: 16,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>Process Console</h2>
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
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <select
            value={eventLevelFilter}
            onChange={(e) => setEventLevelFilter(e.target.value)}
            className="field-input"
            style={{ fontSize: 12, padding: "4px 8px" }}
            aria-label="Filter events by level"
          >
            <option value="all">All Levels</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
          </select>

          <input
            type="search"
            placeholder="Search console..."
            value={eventSearch}
            onChange={(e) => setEventSearch(e.target.value)}
            className="field-input"
            style={{ fontSize: 12, padding: "4px 8px", width: 140 }}
            aria-label="Search console logs"
          />

          <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 4, cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            <span>Auto-scroll</span>
          </label>

          <Button size="compact" variant="subtle" onClick={handleClearConsole}>
            Clear View
          </Button>
          <Button size="compact" variant="secondary" onClick={onRefresh}>
            Refresh Logs
          </Button>
        </div>
      </div>

      <div
        style={{
          maxHeight: 280,
          overflowY: "auto",
          background: "var(--mirror-bg)",
          border: "1px solid var(--border-soft)",
          borderRadius: "var(--radius-sm)",
          padding: "8px 12px",
          fontFamily: "var(--font-mono)",
          fontSize: 12,
          display: "flex",
          flexDirection: "column",
          gap: 4,
        }}
        role="region"
        aria-label="Process events console"
        tabIndex={0}
      >
        {visibleEvents.length === 0 ? (
          <div style={{ color: "var(--muted)", fontStyle: "italic", padding: "12px 0", textAlign: "center" }}>
            No process events recorded.
          </div>
        ) : (
          visibleEvents.map((ev) => {
            const isExpanded = expandedEventIds.has(ev.event_id);
            const color =
              ev.level === "error"
                ? "var(--danger)"
                : ev.level === "warning"
                ? "var(--warn)"
                : "var(--text)";
            return (
              <div
                key={ev.event_id}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 2,
                  borderBottom: "1px solid var(--border-soft)",
                  paddingBottom: 4,
                }}
              >
                <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                  <span style={{ color: "var(--muted)", fontSize: 11, whiteSpace: "nowrap" }}>
                    {new Date(ev.time).toLocaleTimeString()}
                  </span>
                  <span
                    style={{
                      color,
                      fontWeight: 600,
                      fontSize: 10,
                      textTransform: "uppercase",
                      padding: "1px 4px",
                      borderRadius: 3,
                      background:
                        ev.level === "error"
                          ? "var(--danger-soft)"
                          : ev.level === "warning"
                          ? "var(--warn-soft)"
                          : "transparent",
                    }}
                  >
                    {ev.level}
                  </span>
                  <span style={{ color: "var(--accent)", fontWeight: 500 }}>
                    [{ev.stage_id || ev.operation}]
                  </span>
                  <span style={{ color: "var(--text)", flex: 1 }}>{ev.message}</span>
                  {ev.payload && Object.keys(ev.payload).length > 0 && (
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
                      }}
                    >
                      {isExpanded ? "Hide data" : "Data"}
                    </button>
                  )}
                </div>
                {isExpanded && ev.payload && (
                  <pre
                    style={{
                      margin: "4px 0 0 24px",
                      padding: "6px 8px",
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      borderRadius: 4,
                      fontSize: 11,
                      overflowX: "auto",
                    }}
                  >
                    {JSON.stringify(ev.payload, null, 2)}
                  </pre>
                )}
              </div>
            );
          })
        )}
        <div ref={consoleBottomRef} />
      </div>
    </div>
  );
};
