import React from "react";
import { DataTable, TableColumn, StatusBadge, Button } from "../../../components";
import { BookmarkItem } from "../types";
import { InterestRating } from "../../job-evaluation/components/InterestRating";

export interface BookmarksTableProps {
  bookmarks: BookmarkItem[];
  loading?: boolean;
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  selectedJobIds: string[];
  onToggleSelectJob: (runJobId: string) => void;
  onToggleSelectAll: () => void;
  onRemoveSingle: (bookmark: BookmarkItem) => void;
  onInspectEvidence: (bookmark: BookmarkItem) => void;
}

export const BookmarksTable: React.FC<BookmarksTableProps> = ({
  bookmarks,
  loading = false,
  page,
  pageSize,
  total,
  onPageChange,
  selectedJobIds,
  onToggleSelectJob,
  onToggleSelectAll,
  onRemoveSingle,
  onInspectEvidence,
}) => {
  const selectedSet = new Set(selectedJobIds);
  const allSelected =
    bookmarks.length > 0 && bookmarks.every((b) => selectedSet.has(b.run_job_id));

  const columns: TableColumn<BookmarkItem>[] = [
    {
      key: "title",
      header: "Job & Run Context",
      render: (item) => (
        <div style={{ display: "grid", gap: 2 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>{item.title || "Untitled Job"}</span>
          </div>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>
            {item.company} {item.location ? `· ${item.location}` : ""} · Run:{" "}
            <strong>{item.run_name || item.run_id}</strong>
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
      header: "Interest",
      width: "140px",
      render: (item) => (
        <InterestRating
          rating={item.rating}
          disabled={true}
          onChange={() => {}}
          ariaLabelPrefix={`Saved interest for ${item.title}`}
        />
      ),
    },
    {
      key: "cv_status",
      header: "CV Status",
      width: "130px",
      render: (item) => {
        if (item.cv_available) {
          return (
            <span style={{ fontSize: 12, color: "var(--success)", fontWeight: 600 }}>
              ✓ Generated
            </span>
          );
        }
        if (item.cv_generation_status) {
          return <span style={{ fontSize: 12 }}>{item.cv_generation_status}</span>;
        }
        return <span style={{ color: "var(--muted)", fontSize: 12 }}>None</span>;
      },
    },
    {
      key: "bookmarked_at",
      header: "Saved Date",
      width: "140px",
      render: (item) => (
        <span style={{ fontSize: 12, color: "var(--muted)" }}>
          {item.bookmarked_at ? new Date(item.bookmarked_at).toLocaleDateString() : "—"}
        </span>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      width: "150px",
      render: (item) => (
        <div style={{ display: "flex", gap: 6 }}>
          <Button
            size="compact"
            variant="secondary"
            onClick={() => onInspectEvidence(item)}
          >
            Evidence
          </Button>
          <Button
            size="compact"
            variant="danger"
            onClick={() => onRemoveSingle(item)}
            aria-label={`Remove ${item.title} from bookmarks`}
          >
            Remove
          </Button>
        </div>
      ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={bookmarks}
      keyField="run_job_id"
      selectedKeys={selectedSet}
      onToggleSelect={onToggleSelectJob}
      onSelectAll={onToggleSelectAll}
      isAllSelected={allSelected}
      page={page}
      pageSize={pageSize}
      total={total}
      onPageChange={onPageChange}
      emptyMessage={
        loading
          ? "Loading bookmarks..."
          : "No bookmarks saved yet. Bookmark jobs from Run details or Job Evaluation."
      }
    />
  );
};
