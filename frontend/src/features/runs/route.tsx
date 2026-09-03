import React, { useState, useEffect } from "react";
import { RunsListPage } from "./runs-list";
import { RunDetailPage } from "../run-detail/run-detail-page";
import { RunLifecycle } from "./types";

export function parseRunSourceIds(hash: string): string[] {
  const queryIndex = hash.indexOf("?");
  if (queryIndex < 0) return [];
  return Array.from(new URLSearchParams(hash.slice(queryIndex + 1)).getAll("scan_ids"))
    .map((scanId) => scanId.trim())
    .filter(Boolean);
}

export const RunsFeature: React.FC = () => {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [view, setView] = useState<RunLifecycle>("active");
  const [page, setPage] = useState<number>(1);
  const [initialScanIds, setInitialScanIds] = useState<string[]>([]);

  // Sync state with URL hash: e.g. #/runs?view=archived&page=2&run_id=run-123
  useEffect(() => {
    const parseHash = () => {
      const hash = window.location.hash || "#/runs";
      setView("active");
      setPage(1);
      setSelectedRunId(null);
      setInitialScanIds(parseRunSourceIds(hash));
      const parts = hash.split("?");
      if (parts.length > 1) {
        const params = new URLSearchParams(parts[1]);
        const v = params.get("view");
        if (v === "active" || v === "archived" || v === "all") {
          setView(v);
        }
        const p = Number(params.get("page"));
        if (p > 0) {
          setPage(p);
        }
        const id = params.get("run_id");
        setSelectedRunId(id || null);
      }
    };

    parseHash();
    window.addEventListener("hashchange", parseHash);
    return () => window.removeEventListener("hashchange", parseHash);
  }, []);

  const updateUrl = (newView: RunLifecycle, newPage: number, runId: string | null) => {
    const params = new URLSearchParams();
    if (newView !== "active") params.set("view", newView);
    if (newPage > 1) params.set("page", String(newPage));
    if (runId) params.set("run_id", runId);

    const queryString = params.toString();
    const newHash = queryString ? `#/runs?${queryString}` : `#/runs`;
    window.location.hash = newHash;
  };

  const handleViewChange = (newView: RunLifecycle) => {
    setView(newView);
    setPage(1);
    setSelectedRunId(null);
    updateUrl(newView, 1, null);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    updateUrl(view, newPage, selectedRunId);
  };

  const handleSelectRun = (runId: string) => {
    setSelectedRunId(runId);
    updateUrl(view, page, runId);
  };

  const handleBackToList = () => {
    setSelectedRunId(null);
    updateUrl(view, page, null);
  };

  if (selectedRunId) {
    return <RunDetailPage runId={selectedRunId} onBack={handleBackToList} />;
  }

  return (
    <RunsListPage
      view={view}
      page={page}
      onViewChange={handleViewChange}
      onPageChange={handlePageChange}
      onSelectRun={handleSelectRun}
      initialScanIds={initialScanIds}
    />
  );
};

export const route = {
  id: "runs",
  path: "#/runs",
  title: "Runs",
  group: "workspace" as const,
  order: 40,
  component: RunsFeature,
};

export default route;
