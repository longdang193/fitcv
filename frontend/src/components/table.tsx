import React from "react";
import { Button } from "./button";

export interface TableColumn<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  width?: string;
}

export interface DataTableProps<T> {
  columns: TableColumn<T>[];
  data: T[];
  keyField: keyof T | ((item: T) => string);
  selectedKeys?: Set<string>;
  onToggleSelect?: (key: string) => void;
  onSelectAll?: () => void;
  isAllSelected?: boolean;
  page?: number;
  pageSize?: number;
  total?: number;
  onPageChange?: (newPage: number) => void;
  emptyMessage?: string;
  className?: string;
}

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  keyField,
  selectedKeys,
  onToggleSelect,
  onSelectAll,
  isAllSelected,
  page,
  pageSize,
  total,
  onPageChange,
  emptyMessage = "No items found",
  className = "",
}: DataTableProps<T>) {
  const getKey = (item: T): string => {
    if (typeof keyField === "function") {
      return keyField(item);
    }
    return String(item[keyField]);
  };

  const hasSelection = Boolean(selectedKeys && onToggleSelect);
  const totalPages = pageSize && total ? Math.ceil(total / pageSize) : undefined;

  return (
    <div className={`table-card ${className}`.trim()}>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Data table">
        <table className="data-table">
          <thead>
            <tr>
              {hasSelection && (
                <th style={{ width: "40px" }}>
                  <input
                    type="checkbox"
                    aria-label="Select all rows"
                    checked={isAllSelected}
                    onChange={onSelectAll}
                  />
                </th>
              )}
              {columns.map((col) => (
                <th key={col.key} style={{ width: col.width }}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length + (hasSelection ? 1 : 0)}
                  style={{ textAlign: "center", padding: "32px 16px", color: "var(--muted)" }}
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((item) => {
                const key = getKey(item);
                const isSelected = selectedKeys?.has(key);
                return (
                  <tr key={key} className={isSelected ? "is-selected" : undefined}>
                    {hasSelection && (
                      <td>
                        <input
                          type="checkbox"
                          aria-label={`Select row ${key}`}
                          checked={isSelected}
                          onChange={() => {
                            if (onToggleSelect) {
                              onToggleSelect(key);
                            }
                          }}
                        />
                      </td>
                    )}
                    {columns.map((col) => (
                      <td key={col.key}>
                        {col.render ? col.render(item) : item[col.key]}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {page !== undefined && totalPages !== undefined && onPageChange && (
        <div className="table-pagination">
          <span>
            Page {page} of {totalPages || 1} ({total} items)
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <Button
              size="compact"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              aria-label="Previous page"
            >
              Previous
            </Button>
            <Button
              size="compact"
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              aria-label="Next page"
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
