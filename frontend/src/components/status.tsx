import React from "react";

export type StatusVariant = "neutral" | "success" | "warn" | "danger" | "info";

export interface StatusBadgeProps {
  status: StatusVariant;
  label: string;
  icon?: React.ReactNode;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  icon,
  className = "",
}) => {
  const variantClass = `status-badge-${status}`;
  return (
    <span className={`status-badge ${variantClass} ${className}`.trim()}>
      {icon && <span aria-hidden="true">{icon}</span>}
      <span>{label}</span>
    </span>
  );
};

export interface LiveStatusProps {
  message: string;
  level?: "polite" | "assertive";
  className?: string;
}

export const LiveStatus: React.FC<LiveStatusProps> = ({
  message,
  level = "polite",
  className = "",
}) => {
  return (
    <div
      role="status"
      aria-live={level}
      aria-atomic="true"
      className={`live-status-region ${className}`.trim()}
      style={{ minHeight: "1px" }}
    >
      {message}
    </div>
  );
};
