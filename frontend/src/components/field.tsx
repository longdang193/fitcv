import React, { useId } from "react";

export interface FieldProps {
  label: string;
  id?: string;
  name?: string;
  type?: "text" | "number" | "email" | "password" | "search" | "select" | "textarea";
  value?: string | number;
  defaultValue?: string | number;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  hint?: string;
  error?: string;
  rows?: number;
  options?: Array<{ value: string; label: string; disabled?: boolean }>;
  onChange?: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => void;
  className?: string;
}

export const Field: React.FC<FieldProps> = ({
  label,
  id: customId,
  name,
  type = "text",
  value,
  defaultValue,
  placeholder,
  required,
  disabled,
  hint,
  error,
  rows = 3,
  options = [],
  onChange,
  className = "",
}) => {
  const generatedId = useId();
  const fieldId = customId || generatedId;
  const hintId = hint ? `${fieldId}-hint` : undefined;
  const errorId = error ? `${fieldId}-error` : undefined;

  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={`field-group ${className}`.trim()}>
      <label htmlFor={fieldId} className="field-label">
        {label}
        {required && <span className="required-mark" aria-hidden="true">*</span>}
      </label>

      {type === "textarea" ? (
        <textarea
          id={fieldId}
          name={name}
          className="field-textarea"
          value={value}
          defaultValue={defaultValue}
          placeholder={placeholder}
          required={required}
          disabled={disabled}
          rows={rows}
          aria-invalid={error ? "true" : "false"}
          aria-describedby={describedBy}
          onChange={onChange}
        />
      ) : type === "select" ? (
        <select
          id={fieldId}
          name={name}
          className="field-select"
          value={value}
          defaultValue={defaultValue}
          required={required}
          disabled={disabled}
          aria-invalid={error ? "true" : "false"}
          aria-describedby={describedBy}
          onChange={onChange}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} disabled={opt.disabled}>
              {opt.label}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={fieldId}
          name={name}
          type={type}
          className="field-input"
          value={value}
          defaultValue={defaultValue}
          placeholder={placeholder}
          required={required}
          disabled={disabled}
          aria-invalid={error ? "true" : "false"}
          aria-describedby={describedBy}
          onChange={onChange}
        />
      )}

      {hint && (
        <div id={hintId} className="field-hint">
          {hint}
        </div>
      )}
      {error && (
        <div id={errorId} className="field-error" role="alert">
          {error}
        </div>
      )}
    </div>
  );
};
