import React, { useState, useEffect } from "react";
import { ScansListPage } from "./scans-list";
import { ScanDetailPage } from "./scan-detail";
import { ScanLifecycle } from "./types";

export const ScansFeature: React.FC = () => {
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null);
  const [lifecycle, setLifecycle] = useState<ScanLifecycle>("active");
  const [page, setPage] = useState<number>(1);

  // Sync state with URL hash params: e.g. #/scans?lifecycle=archived&page=2&scan_id=scan-123
  useEffect(() => {
    const parseHash = () => {
      const hash = window.location.hash || "#/scans";
      const parts = hash.split("?");
      if (parts.length > 1) {
        const params = new URLSearchParams(parts[1]);
        const tab = params.get("lifecycle");
        if (tab === "active" || tab === "archived") {
          setLifecycle(tab);
        }
        const p = Number(params.get("page"));
        if (p > 0) {
          setPage(p);
        }
        const id = params.get("scan_id");
        setSelectedScanId(id || null);
      } else {
        setSelectedScanId(null);
      }
    };

    parseHash();
    window.addEventListener("hashchange", parseHash);
    return () => window.removeEventListener("hashchange", parseHash);
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
