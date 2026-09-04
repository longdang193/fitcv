import React from "react";
import { RatingEvidenceRow } from "../types";

export interface OptimizationEvidenceTableProps {
  rows?: RatingEvidenceRow[];
  savedRatingsCount?: number;
}

export const OptimizationEvidenceTable: React.FC<OptimizationEvidenceTableProps> = ({
  rows = [],
  savedRatingsCount = 0,
}) => {
  return (
    <div className="table-scroll">
      <table className="run-table">
        <thead>
          <tr>
            <th>Rated</th>
            <th>Run</th>
            <th>Job</th>
            <th>Saved Rank</th>
            <th>Baseline Fit</th>
            <th>User Rating</th>
          </tr>
        </thead>
        <tbody>
          {rows && rows.length > 0 ? (
            rows.map((row, idx) => (
              <tr key={idx}>
                <td>{typeof row.ratedAt === "number" ? new Date(row.ratedAt).toLocaleString() : row.ratedAt}</td>
                <td><span className="run-id">{row.runId}</span></td>
                <td><span className="run-job">{row.job}</span></td>
                <td>{row.savedRank}</td>
                <td>{typeof row.baselineFit === "number" ? row.baselineFit.toFixed(3) : row.baselineFit}</td>
                <td>{row.rating} / 5</td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={6}>
                <div className="empty-state" style={{ textAlign: "center", padding: "32px 16px" }}>
                  <h3 style={{ margin: "0 0 4px", fontSize: 16 }}>
                    {savedRatingsCount > 0 ? "Rating details unavailable" : "No saved ratings"}
                  </h3>
                  <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
                    {savedRatingsCount > 0
                      ? `${savedRatingsCount} saved ratings exist, but row-level details are not available from the current API.`
                      : "Ratings from completed runs will appear here."}
                  </p>
                </div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};
