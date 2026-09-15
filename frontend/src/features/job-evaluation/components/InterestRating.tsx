import React, { useState } from "react";
import { formatOutcomeReason } from "../../../lib/format";

export interface InterestRatingSource {
  capabilities?: { rate?: boolean };
  reason_code?: string | null;
  result_bucket?: string | null;
  status?: string | null;
}

export function getInterestRatingDisabledReason(item: InterestRatingSource): string | undefined {
  if (item.capabilities?.rate !== false) return undefined;
  if (item.reason_code === "not_selected_by_shortlist") {
    return "Rating unavailable: this job was not selected for shortlist decision feedback.";
  }
  const reason = formatOutcomeReason(item.reason_code);
  if (reason) return `Rating unavailable: ${reason}.`;
  if (item.result_bucket === "skipped" || item.status === "skipped") {
    return "Rating unavailable: this job was not selected for decision feedback.";
  }
  return "Rating unavailable: this job is not eligible for decision feedback.";
}

export interface InterestRatingProps {
  rating: number | null | undefined;
  disabled?: boolean;
  disabledReason?: string;
  onChange: (newRating: number | null) => void;
  ariaLabelPrefix?: string;
}

const RATING_LABELS: Record<number, string> = {
  1: "Definitely not interested (1 star)",
  2: "Low application interest (2 stars)",
  3: "Might consider applying (3 stars)",
  4: "Strong application interest (4 stars)",
  5: "Would prioritize applying (5 stars)",
};

export const InterestRating: React.FC<InterestRatingProps> = ({
  rating,
  disabled = false,
  disabledReason,
  onChange,
  ariaLabelPrefix = "Application interest",
}) => {
  const [hovered, setHovered] = useState<number | null>(null);

  const activeVal = hovered !== null ? hovered : (rating || 0);
  const unavailableReason = disabled
    ? disabledReason || "Rating unavailable: this job is not eligible for decision feedback."
    : "";

  return (
    <div
      className="interest-rating"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 2,
        flexWrap: "wrap",
      }}
      role="radiogroup"
      aria-label={`${ariaLabelPrefix}: ${rating ? `${rating} of 5 stars` : "Unrated"}${unavailableReason ? `. ${unavailableReason}` : ""}`}
    >
      {[1, 2, 3, 4, 5].map((star) => {
        const isFilled = star <= activeVal;
        const isCurrent = star === (rating || 0);
        return (
          <button
            key={star}
            type="button"
            className={`star-btn ${isFilled ? "is-filled" : ""}`}
            disabled={disabled}
            role="radio"
            aria-checked={isCurrent}
            aria-label={`Rate ${star} star${star > 1 ? "s" : ""} - ${RATING_LABELS[star]}`}
            onClick={() => {
              if (rating === star) {
                onChange(null);
              } else {
                onChange(star);
              }
            }}
            onMouseEnter={() => !disabled && setHovered(star)}
            onMouseLeave={() => !disabled && setHovered(null)}
          >
            ★
          </button>
        );
      })}

      {rating ? (
        <button
          type="button"
          disabled={disabled}
          className="btn-subtle small-action clear-rating"
          aria-label="Clear interest rating"
          onClick={() => onChange(null)}
        >
          Clear
        </button>
      ) : null}
      {unavailableReason ? (
        <span
          className="interest-rating-unavailable"
          style={{ color: "var(--muted)", fontSize: 11, flexBasis: "100%" }}
        >
          {unavailableReason}
        </span>
      ) : null}
    </div>
  );
};
