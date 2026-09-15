import React, { useState, useEffect } from "react";
import { ScansListPage } from "./scans-list";
import { ScanDetailPage } from "./scan-detail";
import { ScanLifecycle } from "./types";
import { DateRange, parseDateRange } from "../../components/DateRangeFilter";

export interface ScansRouteState {
  lifecycle: ScanLifecycle;
  page: number;
  selectedScanId: string | null;
  dateRange: DateRange;
}

export function parseHash(hash: string): ScansRouteState {
  const query = hash.includes("?") ? hash.slice(hash.indexOf("?") + 1) : "";
  const params = new URLSearchParams(query);
  const lifecycle = params.get("lifecycle");
  const page = Number(params.get("page"));
  const dateRange = parseDateRange(params.get("date_range"));
  return {
    lifecycle: lifecycle === "archived" ? "archived" : "active",
    page: Number.isInteger(page) && page > 0 ? page : 1,
    selectedScanId: params.get("scan_id") || null,
    dateRange,
  };
}

export const ScansFeature: React.FC = () => {
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null);
  const [lifecycle, setLifecycle] = useState<ScanLifecycle>("active");
  const [page, setPage] = useState<number>(1);
  const [dateRange, setDateRange] = useState<DateRange>("today");

  useEffect(() => {
    const readHash = () => {
      const state = parseHash(window.location.hash || "#/scans");
      setLifecycle(state.lifecycle);
      setPage(state.page);
      setSelectedScanId(state.selectedScanId);
      setDateRange(state.dateRange);
    };

    readHash();
    window.addEventListener("hashchange", readHash);
    return () => window.removeEventListener("hashchange", readHash);
  }, []);

  const updateUrl = (
    newLifecycle: ScanLifecycle,
    newPage: number,
    scanId: string | null,
    newDateRange: DateRange = "today"
  ) => {
    const params = new URLSearchParams();
    if (newLifecycle !== "active") params.set("lifecycle", newLifecycle);
    if (newPage > 1) params.set("page", String(newPage));
    if (scanId) params.set("scan_id", scanId);
    if (newDateRange !== "today") params.set("date_range", newDateRange);

    const queryString = params.toString();
    const newHash = queryString ? `#/scans?${queryString}` : `#/scans`;
    window.location.hash = newHash;
  };

  const handleTabChange = (newLifecycle: ScanLifecycle) => {
    setLifecycle(newLifecycle);
    setPage(1);
    setSelectedScanId(null);
    updateUrl(newLifecycle, 1, null, dateRange);
  };

  const handleDateRangeChange = (newRange: DateRange) => {
    setDateRange(newRange);
    setPage(1);
    setSelectedScanId(null);
    updateUrl(lifecycle, 1, null, newRange);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    updateUrl(lifecycle, newPage, selectedScanId, dateRange);
  };

  const handleSelectScan = (scanId: string) => {
    setSelectedScanId(scanId);
    updateUrl(lifecycle, page, scanId, dateRange);
  };

  const handleBackToList = () => {
    setSelectedScanId(null);
    updateUrl(lifecycle, page, null, dateRange);
  };

  if (selectedScanId) {
    return <ScanDetailPage key={selectedScanId} scanId={selectedScanId} onBack={handleBackToList} />;
  }

  return (
    <ScansListPage
      lifecycle={lifecycle}
      page={page}
      dateRange={dateRange}
      onTabChange={handleTabChange}
      onDateRangeChange={handleDateRangeChange}
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
