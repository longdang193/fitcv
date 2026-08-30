import React from "react";
import { DataTable, TableColumn, StatusBadge, Button } from "../../../components";
import { RunJobItem } from "../../runs/types";
import { InterestRating } from "./InterestRating";

export interface JobEvaluationTableProps {
  jobs: RunJobItem[];
  loading?: boolean;
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onToggleBookmark: (job: RunJobItem) => void;
  onChangeInterest: (job: RunJobItem, rating: number | null) => void;
  onInspectEvidence: (job: RunJobItem) => void;
  selectedJobIds?: string[];
  onToggleSelectJob?: (runJobId: string) => void;
  onToggleSelectAll?: () => void;
}

export const JobEvaluationTable: React.FC<JobEvaluationTableProps> = ({
  jobs,
  loading = false,
  page,
  pageSize,
  total,
  onPageChange,
  onToggleBookmark,
  onChangeInterest,
  onInspectEvidence,
  selectedJobIds = [],
  onToggleSelectJob,
  onToggleSelectAll,
}) => {
  const selectedSet = new Set(selectedJobIds);
  const allSelected = jobs.length > 0 && jobs.every((j) => selectedSet.has(j.run_job_id));

  const columns: TableColumn<RunJobItem>[] = [
    {
      key: "bookmark",
      header: "Save",
      width: "60px",
      render: (item) => (
        <button
          type="button"
          className="btn-icon"
          aria-pressed={!!item.bookmarked}
          aria-label={item.bookmarked ? `Remove ${item.title} from bookmarks` : `Bookmark ${item.title}`}
          onClick={() => onToggleBookmark(item)}
          style={{
            border: 0,
            background: "transparent",
            cursor: "pointer",
            fontSize: 18,
            color: item.bookmarked ? "var(--accent)" : "var(--muted)",
            padding: 4,
          }}
        >
          {item.bookmarked ? "★" : "☆"}
        </button>
      ),
    },
    {
      key: "title",
      header: "Job & Company",
      render: (item) => (
        <div style={{ display: "grid", gap: 2 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>{item.title || "Untitled Job"}</span>
          </div>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>
            {item.company} {item.location ? `· ${item.location}` : ""} · <span style={{ fontFamily: "var(--font-mono)" }}>{item.job_id || item.run_job_id}</span>
          </span>
        </div>
      ),
    },
    {
      key: "result_bucket",
      header: "Suitability",
      width: "120px",
      render: (item) => {
        if (item.result_bucket === "passed" || item.status === "passed") {
          return <StatusBadge status="success" label="Passed" />;
        }
        if (item.result_bucket === "rejected" || item.status === "rejected") {
          return <StatusBadge status="danger" label="Rejected" />;
        }
        return <StatusBadge status="neutral" label={item.status || "Pending"} />;
      },
    },
    {
      key: "interest",
      header: "Application Interest",
      width: "160px",
      render: (item) => (
        <InterestRating
          rating={item.interest_rating}
          onChange={(newRating) => onChangeInterest(item, newRating)}
          ariaLabelPrefix={`Application interest for ${item.title}`}
        />
      ),
    },
    {
      key: "actions",
      header: "Fit Evidence",
      width: "120px",
      render: (item) => (
        <Button
          size="compact"
          variant="secondary"
          onClick={() => onInspectEvidence(item)}
        >
          Evidence
        </Button>
      ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={jobs}
      keyField="run_job_id"
      selectedKeys={onToggleSelectJob ? selectedSet : undefined}
      onToggleSelect={onToggleSelectJob}
      onSelectAll={onToggleSelectAll}
      isAllSelected={allSelected}
      page={page}
      pageSize={pageSize}
      total={total}
      onPageChange={onPageChange}
      emptyMessage={loading ? "Loading evaluated jobs..." : "No evaluation results found matching criteria."}
    />
  );
};
