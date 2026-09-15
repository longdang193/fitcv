import React, { useRef } from "react";

export type DateRange = "today" | "24h" | "7d" | "30d" | "all";

export const DATE_RANGES: readonly DateRange[] = [
  "today",
  "24h",
  "7d",
  "30d",
  "all",
];

export const DEFAULT_DATE_RANGE: DateRange = "today";

export const DATE_RANGE_LABELS: Record<DateRange, string> = {
  today: "Today",
  "24h": "24h",
  "7d": "7D",
  "30d": "30D",
  all: "All",
};

export function parseDateRange(value: string | null | undefined): DateRange {
  if (!value) return DEFAULT_DATE_RANGE;
  const normalized = value.trim().toLowerCase();
  if (
    normalized === "today" ||
    normalized === "24h" ||
    normalized === "7d" ||
    normalized === "30d" ||
    normalized === "all"
  ) {
    return normalized as DateRange;
  }
  return DEFAULT_DATE_RANGE;
}

export function getClientTimezone(): string | undefined {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || undefined;
  } catch {
    return undefined;
  }
}

export function getNextDateRangeIndex(
  key: string,
  currentIndex: number,
  length: number = DATE_RANGES.length
): number | null {
  if (length === 0) return null;
  if (key === "ArrowRight" || key === "ArrowDown") return (currentIndex + 1) % length;
  if (key === "ArrowLeft" || key === "ArrowUp") return (currentIndex - 1 + length) % length;
  if (key === "Home") return 0;
  if (key === "End") return length - 1;
  return null;
}

export interface DateRangeFilterProps {
  value: DateRange;
  onChange: (value: DateRange) => void;
  ariaLabel?: string;
  className?: string;
  disabled?: boolean;
}

export const DateRangeFilter: React.FC<DateRangeFilterProps> = ({
  value,
  onChange,
  ariaLabel = "Filter by date range",
  className = "",
  disabled = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const activeRange = parseDateRange(value);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (disabled) return;
    const nextIndex = getNextDateRangeIndex(event.key, index, DATE_RANGES.length);
    if (nextIndex === null) return;
    event.preventDefault();
    const nextRange = DATE_RANGES[nextIndex];
    const buttons = containerRef.current?.querySelectorAll<HTMLButtonElement>("button[role=\"radio\"]");
    buttons?.[nextIndex]?.focus();
    onChange(nextRange);
  };

  return (
    <div
      ref={containerRef}
      className={`date-range-filter ${className}`.trim()}
      role="radiogroup"
      aria-label={ariaLabel}
    >
      {DATE_RANGES.map((range, index) => {
        const selected = range === activeRange;
        return (
          <button
            key={range}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={selected && !disabled ? 0 : -1}
            disabled={disabled}
            className={`date-range-btn ${selected ? "is-active" : ""}`.trim()}
            data-date-range={range}
            onClick={() => {
              if (!disabled) onChange(range);
            }}
            onKeyDown={(event) => handleKeyDown(event, index)}
          >
            {DATE_RANGE_LABELS[range]}
          </button>
        );
      })}
    </div>
  );
};
