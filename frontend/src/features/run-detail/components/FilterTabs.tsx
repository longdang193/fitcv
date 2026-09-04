import React, { useRef } from "react";

export interface FilterTabItem {
  id: string;
  label: string;
  count?: number;
  countColor?: string;
  className?: string;
  dataAttribute?: string;
}

export interface FilterTabsProps {
  items: FilterTabItem[];
  activeId: string;
  onChange: (id: string) => void;
  ariaLabel: string;
  panelId: string;
  className?: string;
}

export function getNextFilterTabIndex(key: string, index: number, length: number): number | null {
  if (length === 0) return null;
  if (key === "ArrowRight" || key === "ArrowDown") return (index + 1) % length;
  if (key === "ArrowLeft" || key === "ArrowUp") return (index - 1 + length) % length;
  if (key === "Home") return 0;
  if (key === "End") return length - 1;
  return null;
}

export const FilterTabs: React.FC<FilterTabsProps> = ({
  items,
  activeId,
  onChange,
  ariaLabel,
  panelId,
  className,
}) => {
  const listRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    const nextIndex = getNextFilterTabIndex(event.key, index, items.length);
    if (nextIndex === null) return;
    event.preventDefault();
    const next = items[nextIndex];
    listRef.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[nextIndex]?.focus();
    onChange(next.id);
  };

  return (
    <div ref={listRef} className={className} role="tablist" aria-label={ariaLabel}>
      {items.map((item, index) => {
        const selected = item.id === activeId;
        return (
          <button
            key={item.id}
            id={`${panelId}-tab-${item.id}`}
            className={item.className || "btn"}
            {...(item.dataAttribute ? { [item.dataAttribute]: item.id } : {})}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls={panelId}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(item.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
          >
            {item.label}
            {typeof item.count === "number" && (
              <strong style={{ marginLeft: 6, color: item.countColor, opacity: item.countColor ? 1 : 0.75 }}>
                {item.count}
              </strong>
            )}
          </button>
        );
      })}
    </div>
  );
};
