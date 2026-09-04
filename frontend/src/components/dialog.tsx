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
  const wasOpenRef = useRef(false);
  const isBackdropMouseDownRef = useRef(false);
  const titleId = useId();
  const descId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (open) {
      if (!wasOpenRef.current) {
        triggerRef.current = (document.activeElement as HTMLElement) || null;
        wasOpenRef.current = true;
      }
      if (dialog && !dialog.open) {
        if (typeof dialog.showModal === "function") {
          dialog.showModal();
        } else {
          dialog.setAttribute("open", "");
        }
      }
    } else if (wasOpenRef.current) {
      wasOpenRef.current = false;
      if (dialog && dialog.open) {
        if (typeof dialog.close === "function") {
          dialog.close();
        } else {
          dialog.removeAttribute("open");
        }
      }
      if (triggerRef.current && typeof triggerRef.current.focus === "function") {
        triggerRef.current.focus();
      }
      triggerRef.current = null;
    }
  }, [open]);

  useEffect(() => {
    return () => {
      if (wasOpenRef.current) {
        wasOpenRef.current = false;
        if (triggerRef.current && typeof triggerRef.current.focus === "function") {
          triggerRef.current.focus();
        }
        triggerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleCancel = (e: Event) => {
      e.preventDefault();
      onClose();
    };

    const handleMouseDown = (e: MouseEvent) => {
      if (e.target === dialog) {
        const rect = dialog.getBoundingClientRect();
        const isInDialog =
          rect.top <= e.clientY &&
          e.clientY <= rect.top + rect.height &&
          rect.left <= e.clientX &&
          e.clientX <= rect.left + rect.width;
        isBackdropMouseDownRef.current = !isInDialog;
      } else {
        isBackdropMouseDownRef.current = false;
      }
    };

    const handleClick = (e: MouseEvent) => {
      const wasBackdropMouseDown = isBackdropMouseDownRef.current;
      isBackdropMouseDownRef.current = false;

      if (!wasBackdropMouseDown || e.target !== dialog) {
        return;
      }

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
    dialog.addEventListener("mousedown", handleMouseDown);
    dialog.addEventListener("click", handleClick);
    return () => {
      dialog.removeEventListener("cancel", handleCancel);
      dialog.removeEventListener("mousedown", handleMouseDown);
      dialog.removeEventListener("click", handleClick);
    };
  }, [open, onClose]);

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
