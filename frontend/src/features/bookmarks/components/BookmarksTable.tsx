import React from "react";
import { DataTable, TableColumn, Button } from "../../../components";
import { BookmarkItem } from "../types";
import { InterestRating } from "../../job-evaluation/components/InterestRating";
import { PipelineOutcome } from "../../job-evaluation/components/PipelineOutcome";
import { formatIdentifier } from "../../../lib/format";
import { extractRequiredJobSkills } from "../../runs/api";

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
  onChangeInterest?: (bookmark: BookmarkItem, rating: number | null) => void;
  onSelectRun?: (runId: string) => void;
  hasFilters?: boolean;
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
  onChangeInterest,
  onSelectRun,
  hasFilters = false,
}) => {
  const selectedSet = new Set(selectedJobIds);
  const allSelected =
    bookmarks.length > 0 && bookmarks.every((b) => selectedSet.has(b.run_job_id));

  const columns: TableColumn<BookmarkItem>[] = [
    {
      key: "run_id",
      header: "Run ID",
      width: "150px",
      render: (item) => {
        if (onSelectRun) {
          return (
            <button
              type="button"
              className="run-id-link"
              onClick={() => onSelectRun(item.run_id)}
              aria-label={`Open details for ${item.run_id}`}
              style={{
                background: "transparent",
                border: 0,
                padding: 0,
                color: "var(--accent)",
                cursor: "pointer",
                textDecoration: "none",
                fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace",
                fontWeight: 700,
                fontSize: 12,
              }}
            >
              <span title={item.run_id}>{formatIdentifier(item.run_id)}</span>
            </button>
          );
        }
        return (
          <span
            style={{
              fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace",
              fontWeight: 700,
              fontSize: 12,
            }}
          >
            <span title={item.run_id}>{formatIdentifier(item.run_id)}</span>
          </span>
        );
      },
    },
    {
      key: "title",
      header: "Job & Actions",
      render: (item) => (
        <div style={{ display: "grid", gap: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {(item as any).source_url || (item as any).url ? <a
              href={(item as any).source_url || (item as any).url || "#"}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: "var(--accent)",
                fontWeight: 600,
                fontSize: 14,
                textDecoration: "none",
              }}
            >
              {item.title || "Untitled Job"}
            </a> : <strong style={{ fontSize: 14 }}>{item.title || "Untitled Job"}</strong>}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <InterestRating
              rating={item.rating}
              disabled={!onChangeInterest}
              onChange={(newRating) => onChangeInterest?.(item, newRating)}
              ariaLabelPrefix={`Application Interest for ${item.title}`}
            />
          </div>
        </div>
      ),
    },
    {
      key: "attributes",
      header: "Job Attributes",
      render: (item) => {
        const attrs: [string, string | undefined][] = [
          ["Location", item.location || (item as any).city],
          ["Work Mode", (item as any).work_mode || (item as any).workMode],
          ["Language", (item as any).language],
          ["Seniority", (item as any).seniority],
          ["Job Family", (item as any).role_family || (item as any).job_family || (item as any).jobFamily],
          ["Domain", (item as any).domain || (item as any).industry],
        ];
        return (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, minmax(90px, 1fr))",
              gap: "4px 10px",
              fontSize: 12,
            }}
          >
            {attrs.map(([label, val]) => (
              <div key={label} style={{ display: "grid" }}>
                <span style={{ color: "var(--muted)", fontSize: 10, fontWeight: 700, textTransform: "uppercase" }}>
                  {label}
                </span>
                <strong>{val || "—"}</strong>
              </div>
            ))}
          </div>
        );
      },
    },
    {
      key: "skills",
      header: "Required Skills",
      render: (item) => {
        const skillsList = extractRequiredJobSkills(item);
        if (skillsList.length === 0) {
          return <span style={{ color: "var(--muted)", fontSize: 12 }}>—</span>;
        }
        const visible = skillsList.slice(0, 5);
        const extra = skillsList.length - visible.length;
        return (
          <div className="skill-list">
            {visible.map((s, idx) => (
              <span key={idx} className="skill-chip">
                {s}
              </span>
            ))}
            {extra > 0 && <span className="skill-chip">+{extra} more</span>}
          </div>
        );
      },
    },
    {
      key: "result_bucket",
      header: "Pipeline Outcome",
      width: "180px",
      render: (item) => <PipelineOutcome item={item} />,
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
      className="bookmarks-table"
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
          : hasFilters
          ? "No bookmarks match this view. Change the pipeline stage or search to see other bookmarked jobs."
          : "No bookmarked jobs yet. Add bookmarks from Run Details to collect jobs here."
      }
    />
  );
};
