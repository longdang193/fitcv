import React, { useEffect, useRef, useId } from "react";
import { Button } from "./button";

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

export const Dialog: React.FC<DialogProps> = ({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  className = "",
}) => {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);
  const titleId = useId();
  const descId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open) {
      triggerRef.current = document.activeElement as HTMLElement;
      if (!dialog.open) {
        dialog.showModal();
      }
    } else {
      if (dialog.open) {
        dialog.close();
      }
      if (triggerRef.current) {
        triggerRef.current.focus();
      }
    }
  }, [open]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleCancel = (e: Event) => {
      e.preventDefault();
      onClose();
    };

    const handleClick = (e: MouseEvent) => {
      const rect = dialog.getBoundingClientRect();
      const isInDialog =
        rect.top <= e.clientY &&
        e.clientY <= rect.top + rect.height &&
        rect.left <= e.clientX &&
        e.clientX <= rect.left + rect.width;
      if (!isInDialog) {
        onClose();
      }
    };

    dialog.addEventListener("cancel", handleCancel);
    dialog.addEventListener("click", handleClick);
    return () => {
      dialog.removeEventListener("cancel", handleCancel);
      dialog.removeEventListener("click", handleClick);
    };
  }, [onClose]);

  if (!open) return null;

  return (
    <dialog
      ref={dialogRef}
      className={`native-dialog ${className}`.trim()}
      aria-labelledby={titleId}
      aria-describedby={description ? descId : undefined}
    >
      <div className="dialog-header">
        <h2 id={titleId} className="dialog-title">
          {title}
        </h2>
        {description && (
          <p id={descId} className="dialog-description">
            {description}
          </p>
        )}
      </div>

      <div className="dialog-body">{children}</div>

      <div className="dialog-footer">
        {footer ? (
          footer
        ) : (
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        )}
      </div>
    </dialog>
  );
};
