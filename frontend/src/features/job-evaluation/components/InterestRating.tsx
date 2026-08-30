import React, { useState } from "react";

export interface InterestRatingProps {
  rating: number | null | undefined;
  disabled?: boolean;
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
  onChange,
  ariaLabelPrefix = "Application interest",
}) => {
  const [hovered, setHovered] = useState<number | null>(null);

  const activeVal = hovered !== null ? hovered : (rating || 0);

  return (
    <div
      className="interest-rating"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 2,
        whiteSpace: "nowrap",
      }}
      role="group"
      aria-label={`${ariaLabelPrefix}: ${rating ? `${rating} of 5 stars` : "Unrated"}`}
    >
      {[1, 2, 3, 4, 5].map((star) => {
        const isFilled = star <= activeVal;
        const isCurrent = star === (rating || 0);
        return (
          <button
            key={star}
            type="button"
            className="star-btn"
            disabled={disabled}
            aria-pressed={isCurrent}
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
            style={{
              padding: "2px 4px",
              border: 0,
              background: "transparent",
              cursor: disabled ? "not-allowed" : "pointer",
              fontSize: 18,
              lineHeight: 1,
              color: isFilled ? "#d99720" : "var(--border)",
              opacity: disabled ? 0.6 : 1,
              transition: "color 0.15s ease",
            }}
          >
            ★
          </button>
        );
      })}

      {rating ? (
        <button
          type="button"
          disabled={disabled}
          className="btn-subtle"
          aria-label="Clear interest rating"
          onClick={() => onChange(null)}
          style={{
            marginLeft: 4,
            fontSize: 12,
            padding: "2px 4px",
            border: 0,
            background: "transparent",
            cursor: disabled ? "not-allowed" : "pointer",
            color: "var(--muted)",
          }}
        >
          ✕
        </button>
      ) : null}
    </div>
  );
};
