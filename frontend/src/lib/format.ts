const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

export function formatTimestamp(value: string | number | Date | null | undefined, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? fallback : dateTimeFormatter.format(date);
}

export function formatIdentifier(value: string | null | undefined, hashLength = 8): string {
  if (!value || value.length <= hashLength) return value || "—";
  const separator = value.lastIndexOf("_");
  if (separator > 0 && separator < value.length - 1) {
    return `${value.slice(0, separator + 1)}${value.slice(separator + 1, separator + 1 + hashLength)}…`;
  }
  return `${value.slice(0, hashLength)}…`;
}

export function formatOutcomeCode(value: string | null | undefined): string {
  if (value === "advanced") return "Advanced to next stage";
  return value || "";
}

const STATUS_VALUE_MAP: Record<string, string> = {
  ranked_with_cv: "Ranked with CV",
  ranked_no_cv: "Ranked without CV",
  ranked_blocked_by_reranker_fit: "Blocked by reranker fit",
  blocked_by_reranker_fit: "Blocked by reranker fit",
  reranker_fit_below_threshold: "Reranker fit below threshold",
  scored_not_ranked: "Scored not ranked",
  ranked_skipped_fit_gate: "Skipped fit gate",
};

const FACTOR_LABEL_MAP: Record<string, string> = {
  evidence_ref: "Evidence Reference",
  pipeline_status: "Pipeline Status",
  skip_is_terminal_rejection: "Skip Terminal Rejection",
  reranker_fit: "Reranker Fit",
};

export function formatFactorLabel(key: string | null | undefined): string {
  if (!key) return "";
  const trimmed = key.trim();
  const lower = trimmed.toLowerCase();
  if (FACTOR_LABEL_MAP[lower]) {
    return FACTOR_LABEL_MAP[lower];
  }
  if (/^[a-z0-9_-]+$/i.test(trimmed) && (trimmed.includes("_") || trimmed.includes("-"))) {
    const words = trimmed.split(/[_-]+/).filter(Boolean);
    return words.map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(" ");
  }
  return trimmed;
}

export interface FormattedFactorValue {
  label: string;
  variant: "success" | "danger" | "neutral" | "info";
  reason?: string;
}

export function formatFactorValue(val: unknown): FormattedFactorValue {
  if (val === null || val === undefined) {
    return { label: "—", variant: "neutral" };
  }
  if (typeof val === "boolean") {
    return {
      label: val ? "Yes" : "No",
      variant: val ? "info" : "neutral",
    };
  }
  if (typeof val === "string") {
    const trimmed = val.trim();
    const formatted = STATUS_VALUE_MAP[trimmed.toLowerCase()] || formatOutcomeReason(trimmed) || trimmed;
    const lower = trimmed.toLowerCase();
    const isDanger = lower.includes("blocked") || lower.includes("rejected") || lower.includes("below");
    const isSuccess = lower.includes("passed") || lower.includes("with_cv") || lower === "ranked";
    return {
      label: formatted,
      variant: isDanger ? "danger" : isSuccess ? "success" : "neutral",
    };
  }
  if (typeof val === "number") {
    return { label: String(val), variant: "neutral" };
  }
  if (typeof val === "object") {
    const obj = val as Record<string, any>;
    if (typeof obj.passed === "boolean") {
      return {
        label: obj.passed ? "✓ Met" : "✕ Missing / Below threshold",
        variant: obj.passed ? "success" : "danger",
        reason: obj.reason ? formatOutcomeReason(obj.reason) : undefined,
      };
    }
    if (obj.artifact) {
      return {
        label: String(obj.artifact),
        variant: "neutral",
        reason: obj.reason ? formatOutcomeReason(obj.reason) : undefined,
      };
    }
    if (obj.status) {
      const statusStr = String(obj.status).trim();
      const formatted = STATUS_VALUE_MAP[statusStr.toLowerCase()] || formatOutcomeReason(statusStr) || statusStr;
      const lower = statusStr.toLowerCase();
      const isDanger = lower.includes("blocked") || lower.includes("rejected") || lower.includes("below");
      const isSuccess = lower.includes("passed") || lower.includes("with_cv") || lower === "ranked";
      return {
        label: formatted,
        variant: isDanger ? "danger" : isSuccess ? "success" : "neutral",
        reason: obj.reason ? formatOutcomeReason(obj.reason) : undefined,
      };
    }
    if (obj.text || obj.id) {
      return {
        label: String(obj.text || obj.id),
        variant: "neutral",
        reason: obj.reason ? formatOutcomeReason(obj.reason) : undefined,
      };
    }
    return {
      label: JSON.stringify(val),
      variant: "neutral",
    };
  }
  return { label: String(val), variant: "neutral" };
}

export function formatOutcomeReason(item: unknown): string {
  if (!item) return "";
  if (typeof item === "string") {
    const trimmed = item.trim();
    if (!trimmed) return "";
    const lower = trimmed.toLowerCase();
    if (STATUS_VALUE_MAP[lower]) return STATUS_VALUE_MAP[lower];
    if (/^[a-z0-9_-]+$/i.test(trimmed) && (trimmed.includes("_") || trimmed.includes("-"))) {
      const words = trimmed.split(/[_-]+/).filter(Boolean);
      return words.map((w, i) => i === 0 ? w.charAt(0).toUpperCase() + w.slice(1).toLowerCase() : w.toLowerCase()).join(" ");
    }
    return trimmed;
  }
  if (typeof item !== "object") return "";
  const obj = item as Record<string, any>;
  const evidence = (obj.evidence && typeof obj.evidence === "object") ? obj.evidence : {};
  const outcome = (obj.outcome && typeof obj.outcome === "object") ? obj.outcome : {};

  const candidate =
    outcome.detail ||
    obj.stage_outcome_reason ||
    evidence.stage_outcome_reason ||
    evidence.detail ||
    evidence.outcome?.detail ||
    obj.reason_detail ||
    obj.reject_reason ||
    obj.reason ||
    obj.reason_code ||
    evidence.reason_code ||
    "";

  if (typeof candidate !== "string") return "";
  const trimmed = candidate.trim();
  if (!trimmed) return "";
  const lower = trimmed.toLowerCase();
  if (STATUS_VALUE_MAP[lower]) return STATUS_VALUE_MAP[lower];

  if (/^[a-z0-9_-]+$/i.test(trimmed) && (trimmed.includes("_") || trimmed.includes("-"))) {
    const words = trimmed.split(/[_-]+/).filter(Boolean);
    return words.map((w, i) => i === 0 ? w.charAt(0).toUpperCase() + w.slice(1).toLowerCase() : w.toLowerCase()).join(" ");
  }
  return trimmed;
}
