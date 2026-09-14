import React, { useState, useEffect } from "react";
import { ScansListPage } from "./scans-list";
import { ScanDetailPage } from "./scan-detail";
import { ScanLifecycle } from "./types";

export interface ScansRouteState {
  lifecycle: ScanLifecycle;
  page: number;
  selectedScanId: string | null;
}

export function parseHash(hash: string): ScansRouteState {
  const query = hash.includes("?") ? hash.slice(hash.indexOf("?") + 1) : "";
  const params = new URLSearchParams(query);
  const lifecycle = params.get("lifecycle");
  const page = Number(params.get("page"));
  return {
    lifecycle: lifecycle === "archived" ? "archived" : "active",
    page: Number.isInteger(page) && page > 0 ? page : 1,
    selectedScanId: params.get("scan_id") || null,
  };
}

export const ScansFeature: React.FC = () => {
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null);
  const [lifecycle, setLifecycle] = useState<ScanLifecycle>("active");
  const [page, setPage] = useState<number>(1);

  // Sync state with URL hash params: e.g. #/scans?lifecycle=archived&page=2&scan_id=scan-123
  useEffect(() => {
    const readHash = () => {
      const state = parseHash(window.location.hash || "#/scans");
      setLifecycle(state.lifecycle);
      setPage(state.page);
      setSelectedScanId(state.selectedScanId);
    };

    readHash();
    window.addEventListener("hashchange", readHash);
    return () => window.removeEventListener("hashchange", readHash);
  }, []);

  const updateUrl = (newLifecycle: ScanLifecycle, newPage: number, scanId: string | null) => {
    const params = new URLSearchParams();
    if (newLifecycle !== "active") params.set("lifecycle", newLifecycle);
    if (newPage > 1) params.set("page", String(newPage));
    if (scanId) params.set("scan_id", scanId);

    const queryString = params.toString();
    const newHash = queryString ? `#/scans?${queryString}` : `#/scans`;
    window.location.hash = newHash;
  };

  const handleTabChange = (newLifecycle: ScanLifecycle) => {
    setLifecycle(newLifecycle);
    setPage(1);
    setSelectedScanId(null);
    updateUrl(newLifecycle, 1, null);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    updateUrl(lifecycle, newPage, selectedScanId);
  };

  const handleSelectScan = (scanId: string) => {
    setSelectedScanId(scanId);
    updateUrl(lifecycle, page, scanId);
  };

  const handleBackToList = () => {
    setSelectedScanId(null);
    updateUrl(lifecycle, page, null);
  };

  if (selectedScanId) {
    return <ScanDetailPage scanId={selectedScanId} onBack={handleBackToList} />;
  }

  return (
    <ScansListPage
      lifecycle={lifecycle}
      page={page}
      onTabChange={handleTabChange}
      onPageChange={handlePageChange}
      onSelectScan={handleSelectScan}
    />
  );
};

export const route = {
  id: "scans",
  path: "#/scans",
  title: "Scans",
  group: "workspace" as const,
  order: 30,
  component: ScansFeature,
};

export default route;
