import React, { useRef, useId } from "react";

export interface TabItem {
  id: string;
  label: string;
  count?: number;
  disabled?: boolean;
}

export interface TabsProps {
  items: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  ariaLabel?: string;
  children?: React.ReactNode;
}

export const Tabs: React.FC<TabsProps> = ({
  items,
  activeId,
  onChange,
  ariaLabel = "Tabs",
  children,
}) => {
  const tabListRef = useRef<HTMLDivElement>(null);
  const baseId = useId();

  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    const enabledIndices = items
      .map((t, idx) => (!t.disabled ? idx : -1))
      .filter((idx) => idx !== -1);

    const currentPos = enabledIndices.indexOf(index);
    let nextIndex = -1;

    if (e.key === "ArrowRight") {
      e.preventDefault();
      nextIndex = enabledIndices[(currentPos + 1) % enabledIndices.length];
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      nextIndex = enabledIndices[(currentPos - 1 + enabledIndices.length) % enabledIndices.length];
    } else if (e.key === "Home") {
      e.preventDefault();
      nextIndex = enabledIndices[0];
    } else if (e.key === "End") {
      e.preventDefault();
      nextIndex = enabledIndices[enabledIndices.length - 1];
    }

    if (nextIndex !== -1 && tabListRef.current) {
      const buttons = tabListRef.current.querySelectorAll<HTMLButtonElement>('[role="tab"]');
      buttons[nextIndex]?.focus();
      onChange(items[nextIndex].id);
    }
  };

  return (
    <div className="tabs-container">
      <div
        ref={tabListRef}
        className="tab-list"
        role="tablist"
        aria-label={ariaLabel}
      >
        {items.map((item, index) => {
          const isSelected = item.id === activeId;
          const tabId = `${baseId}-tab-${item.id}`;
          const panelId = `${baseId}-panel-${item.id}`;

          return (
            <button
              key={item.id}
              id={tabId}
              role="tab"
              type="button"
              className="tab-button"
              aria-selected={isSelected}
              aria-controls={panelId}
              tabIndex={isSelected ? 0 : -1}
              disabled={item.disabled}
              onClick={() => onChange(item.id)}
              onKeyDown={(e) => handleKeyDown(e, index)}
            >
              {item.label}
              {typeof item.count === "number" && (
                <span className="tab-count" style={{ marginLeft: 6, opacity: 0.75 }}>
                  ({item.count})
                </span>
              )}
            </button>
          );
        })}
      </div>

      {children && (
        <div
          id={`${baseId}-panel-${activeId}`}
          role="tabpanel"
          aria-labelledby={`${baseId}-tab-${activeId}`}
          tabIndex={0}
          className="tab-panel"
        >
          {children}
        </div>
      )}
    </div>
  );
};
