import React, { useCallback, useEffect, useState } from "react";
import { Button } from "../../components";
import { fetchAnalyticsDashboard, fetchAnalyticsTrace } from "./api";
import { AnalyticsDashboardData, AnalyticsTraceData } from "./types";

function value(row: Record<string, unknown>, key: string): string {
  const raw = row[key];
  return raw === null || raw === undefined || raw === "" ? "—" : String(raw);
}

const ProjectionTable: React.FC<{
  title: string;
  rows: Array<Record<string, unknown>>;
  columns: string[];
}> = ({ title, rows, columns }) => (
  <section className="section-card" aria-labelledby={`${title}-heading`}>
    <h3 id={`${title}-heading`}>{title}</h3>
    {rows.length === 0 ? (
      <p role="status">No published rows.</p>
    ) : (
      <div style={{ overflowX: "auto" }} tabIndex={0} aria-label={`${title} table`}>
        <table className="data-table">
          <thead>
            <tr>{columns.map((column) => <th key={column} scope="col">{column.replaceAll("_", " ")}</th>)}</tr>
          </thead>
          <tbody>
            {rows.slice(0, 25).map((row, index) => (
              <tr key={`${title}-${index}`}>
                {columns.map((column) => <td key={column}>{value(row, column)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </section>
);

export const AnalyticsDashboardPage: React.FC = () => {
  const [data, setData] = useState<AnalyticsDashboardData | null>(null);
  const [trace, setTrace] = useState<AnalyticsTraceData | null>(null);
  const [postingId, setPostingId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await fetchAnalyticsDashboard());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Analytics could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const loadTrace = async () => {
    const normalized = postingId.trim();
    if (!normalized) return;
    try {
      setTrace(await fetchAnalyticsTrace(normalized));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Posting trace could not be loaded.");
    }
  };

  return (
    <div className="content-container analytics-dashboard" aria-busy={loading}>
      <div className="page-head">
        <div>
          <p className="eyebrow">Evidence workspace</p>
          <h2>Analytics</h2>
          <p>Imported opportunity and candidate evidence projections. No market-wide claims.</p>
        </div>
      </div>
      {loading && <p role="status">Loading published analytics…</p>}
      {error && <div className="notice error" role="alert">{error} <Button onClick={() => void load()}>Retry</Button></div>}
      {!loading && !error && data?.coverage.status === "unavailable" && (
        <div className="notice warn" role="status">
          Published analytics unavailable. {data.coverage.unavailable_reasons.join(", ") || "Refresh the analytics release."}
        </div>
      )}
      {!loading && !error && data?.coverage.status === "available" && (
        <>
          <section className="section-card" aria-labelledby="coverage-heading">
            <h3 id="coverage-heading">Coverage</h3>
            <p>Sample: {data.coverage.sample_size}. Sources: {data.coverage.source_mix.join(", ") || "—"}.</p>
            <p>Collection: {data.coverage.collection_window.start || "—"} to {data.coverage.collection_window.end || "—"}.</p>
            <p>Source commit: <code>{String(data.metadata.source_commit || "—")}</code></p>
          </section>
          <ProjectionTable title="Opportunity landscape" rows={data.opportunity_landscape} columns={["requirement", "cohort_id", "numerator_posting_count", "denominator_posting_count"]} />
          <ProjectionTable title="Requirement demand" rows={data.requirement_demand} columns={["dimension_key", "numerator", "denominator", "value", "coverage_status"]} />
          <ProjectionTable title="Candidate evidence gaps" rows={data.candidate_evidence_gaps} columns={["requirement", "gap_category", "candidate_profile_revision", "coverage", "unavailable_reason"]} />
          <section className="section-card" aria-labelledby="trace-heading">
            <h3 id="trace-heading">Posting traceability</h3>
            <form onSubmit={(event) => { event.preventDefault(); void loadTrace(); }}>
              <label htmlFor="posting-id">Posting ID</label>
              <input id="posting-id" value={postingId} onChange={(event) => setPostingId(event.target.value)} />
              <Button type="submit">Inspect source</Button>
            </form>
            {trace?.posting && <pre style={{ overflowX: "auto" }}>{JSON.stringify(trace, null, 2)}</pre>}
          </section>
        </>
      )}
    </div>
  );
};

export const route = {
  id: "analytics-dashboard",
  path: "#/analytics",
  title: "Analytics",
  group: "workspace" as const,
  order: 40,
  component: AnalyticsDashboardPage,
};

export default route;
