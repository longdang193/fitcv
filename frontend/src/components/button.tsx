import React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "subtle" | "icon";
  size?: "default" | "compact" | "sm";
  loading?: boolean;
  icon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = "secondary",
      size = "default",
      loading = false,
      disabled = false,
      icon,
      className = "",
      type = "button",
      ...rest
    },
    ref
  ) => {
    const variantClass =
      variant === "primary"
        ? "btn-primary"
        : variant === "danger"
        ? "btn-danger"
        : variant === "subtle"
        ? "btn-subtle"
        : variant === "icon"
        ? "btn-icon"
        : "btn-secondary";

    const sizeClass = size === "compact" || size === "sm" ? "btn-compact" : "";
    const classes = ["btn", variantClass, sizeClass, className].filter(Boolean).join(" ");

    return (
      <button
        ref={ref}
        type={type}
        className={classes}
        disabled={disabled || loading}
        aria-busy={loading ? "true" : undefined}
        {...rest}
      >
        {loading ? (
          <span className="btn-spinner" aria-hidden="true">
            ...
          </span>
        ) : (
          icon && <span className="btn-icon-wrapper">{icon}</span>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
