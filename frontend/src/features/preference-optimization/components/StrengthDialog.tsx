import React, { useState, useEffect } from "react";
import { Dialog, Button } from "../../../components";
import { PersonalizationBounds } from "../types";

export interface StrengthDialogProps {
  open: boolean;
  onClose: () => void;
  currentStrength: number;
  bounds: PersonalizationBounds;
  onSave: (strength: number) => Promise<void> | void;
  saving?: boolean;
}

export const StrengthDialog: React.FC<StrengthDialogProps> = ({
  open,
  onClose,
  currentStrength,
  bounds,
  onSave,
  saving = false,
}) => {
  const [value, setValue] = useState<string>(currentStrength.toFixed(2));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setValue(currentStrength.toFixed(2));
      setError(null);
    }
  }, [open, currentStrength]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const num = parseFloat(value);
    if (isNaN(num)) {
      setError("Please enter a valid number.");
      return;
    }
    if (num < bounds.minimum || num > bounds.maximum) {
      setError(`Value must be between ${bounds.minimum.toFixed(2)} and ${bounds.maximum.toFixed(2)}.`);
      return;
    }
    const rounded = Math.round(num / bounds.step) * bounds.step;
    await onSave(rounded);
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Personalization Strength"
      description="Set how strongly saved ratings can influence future personalized rankings."
      footer={
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button variant="primary" type="submit" form="personalizationStrengthForm" disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </div>
      }
    >
      <form id="personalizationStrengthForm" className="weight-form" onSubmit={handleSubmit}>
        <div className="weight-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}>
          <div>
            <label htmlFor="personalizationStrengthInput" style={{ fontWeight: 600, display: "block" }}>
              Strength
            </label>
            <span style={{ fontSize: 13, color: "var(--muted)", display: "block" }}>
              Higher values let saved ratings move results further from Baseline Ranking.
            </span>
          </div>
          <input
            id="personalizationStrengthInput"
            className="field"
            type="number"
            min={bounds.minimum}
            max={bounds.maximum}
            step={bounds.step}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              setError(null);
            }}
            required
            style={{ width: 120, textAlign: "right" }}
            aria-label="Personalization Strength Value"
          />
        </div>
        <p className="weight-status" id="personalizationStrengthStatus" style={{ marginTop: 12, fontSize: 12, color: error ? "var(--danger)" : "var(--muted)" }}>
          {error || `Choose a value from ${bounds.minimum.toFixed(2)} to ${bounds.maximum.toFixed(2)}.`}
        </p>
      </form>
    </Dialog>
  );
};
