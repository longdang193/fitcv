import React from "react";
import { Button } from "./button";

export interface LoadingStateProps {
  message?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = "Loading...",
  className = "",
}) => (
  <div
    className={`state-container loading-state ${className}`.trim()}
    role="status"
    aria-busy="true"
    style={{ display: "grid", placeItems: "center", padding: "48px 24px", color: "var(--muted)" }}
  >
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <span style={{ fontSize: 16 }}>⏳</span>
      <span>{message}</span>
    </div>
  </div>
);

export interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  actionLabel,
  onAction,
  className = "",
}) => (
  <div
    className={`state-container empty-state ${className}`.trim()}
    style={{ display: "grid", placeItems: "center", textAlign: "center", padding: "56px 24px", gap: 8 }}
  >
    {icon && <div style={{ fontSize: 32, color: "var(--accent)" }}>{icon}</div>}
    <h3 style={{ margin: "4px 0 0", fontSize: 17, fontFamily: "var(--display-font)" }}>{title}</h3>
    {description && <p style={{ maxWidth: 440, margin: 0, color: "var(--muted)", fontSize: 13 }}>{description}</p>}
    {actionLabel && onAction && (
      <div style={{ marginTop: 12 }}>
        <Button variant="primary" onClick={onAction}>
          {actionLabel}
        </Button>
      </div>
    )}
  </div>
);

export interface ErrorStateProps {
  title?: string;
  message: string;
  actionLabel?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Something went wrong",
  message,
  actionLabel = "Retry",
  onRetry,
  className = "",
}) => (
  <div
    className={`state-container error-state ${className}`.trim()}
    role="alert"
    style={{
      display: "grid",
      placeItems: "center",
      textAlign: "center",
      padding: "48px 24px",
      gap: 8,
      border: "1px solid var(--danger-soft)",
      borderRadius: "var(--radius-lg)",
      background: "var(--surface)",
    }}
  >
    <div style={{ fontSize: 32, color: "var(--danger)" }}>⚠️</div>
    <h3 style={{ margin: "4px 0 0", fontSize: 17, color: "var(--danger)" }}>{title}</h3>
    <p style={{ maxWidth: 480, margin: 0, color: "var(--muted)", fontSize: 13 }}>{message}</p>
    {onRetry && (
      <div style={{ marginTop: 12 }}>
        <Button variant="secondary" onClick={onRetry}>
          {actionLabel}
        </Button>
      </div>
    )}
  </div>
);

export interface SuccessStateProps {
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const SuccessState: React.FC<SuccessStateProps> = ({
  title,
  description,
  actionLabel,
  onAction,
  className = "",
}) => (
  <div
    className={`state-container success-state ${className}`.trim()}
    style={{
      display: "grid",
      placeItems: "center",
      textAlign: "center",
      padding: "48px 24px",
      gap: 8,
      border: "1px solid var(--success-soft)",
      borderRadius: "var(--radius-lg)",
      background: "var(--surface)",
    }}
  >
    <div style={{ fontSize: 32, color: "var(--success)" }}>✓</div>
    <h3 style={{ margin: "4px 0 0", fontSize: 17, color: "var(--success)" }}>{title}</h3>
    {description && <p style={{ maxWidth: 480, margin: 0, color: "var(--muted)", fontSize: 13 }}>{description}</p>}
    {actionLabel && onAction && (
      <div style={{ marginTop: 12 }}>
        <Button variant="primary" onClick={onAction}>
          {actionLabel}
        </Button>
      </div>
    )}
  </div>
);

export interface ZeroResultsStateProps {
  query?: string;
  filterDescription?: string;
  onClear?: () => void;
  clearLabel?: string;
  className?: string;
}

export const ZeroResultsState: React.FC<ZeroResultsStateProps> = ({
  query,
  filterDescription,
  onClear,
  clearLabel = "Clear filters",
  className = "",
}) => (
  <div
    className={`state-container zero-results-state empty-state ${className}`.trim()}
    role="status"
    aria-live="polite"
    style={{
      display: "grid",
      placeItems: "center",
      textAlign: "center",
      padding: "48px 24px",
      gap: 8,
    }}
  >
    <div style={{ fontSize: 28, color: "var(--muted)" }} aria-hidden="true">
      🔍
    </div>
    <h3 style={{ margin: "4px 0 0", fontSize: 16, fontWeight: 600 }}>
      {query ? `No results for "${query}"` : "No matching results"}
    </h3>
    <p style={{ maxWidth: 440, margin: 0, color: "var(--muted)", fontSize: 13 }}>
      {filterDescription ||
        "No items match your active search or filter criteria. Try adjusting keywords or clearing active filters."}
    </p>
    {onClear && (
      <div style={{ marginTop: 12 }}>
        <Button variant="secondary" size="compact" onClick={onClear}>
          {clearLabel}
        </Button>
      </div>
    )}
  </div>
);
