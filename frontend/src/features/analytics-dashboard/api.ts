import { apiClient } from "../../lib/api-client";
import { AnalyticsDashboardData, AnalyticsTraceData } from "./types";

export async function fetchAnalyticsDashboard(): Promise<AnalyticsDashboardData> {
  const response = await apiClient.get<{ data: AnalyticsDashboardData }>("/analytics/semantic-metrics");
  return response.data.data;
}

export async function fetchAnalyticsTrace(postingId: string): Promise<AnalyticsTraceData> {
  const response = await apiClient.get<{ data: AnalyticsTraceData }>(
    `/analytics/trace/${encodeURIComponent(postingId)}`
  );
  return response.data.data;
}
