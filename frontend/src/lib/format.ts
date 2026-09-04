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

export function formatOutcomeReason(item: unknown): string {
  if (!item || typeof item !== "object") return "";
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

  if (/^[a-z0-9_-]+$/i.test(trimmed) && (trimmed.includes("_") || trimmed.includes("-"))) {
    const words = trimmed.split(/[_-]+/).filter(Boolean);
    return words.map((w, i) => i === 0 ? w.charAt(0).toUpperCase() + w.slice(1).toLowerCase() : w.toLowerCase()).join(" ");
  }
  return trimmed;
}
