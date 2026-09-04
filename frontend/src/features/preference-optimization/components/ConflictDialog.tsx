import React from "react";
import { Dialog, Button } from "../../../components";

export interface ConflictDialogProps {
  open: boolean;
  onClose: () => void;
  onReload: () => void;
  message?: string | null;
}

export const ConflictDialog: React.FC<ConflictDialogProps> = ({
  open,
  onClose,
  onReload,
  message,
}) => {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Settings Conflict (409)"
      description={message || "Settings changed since last read."}
      footer={
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <Button variant="secondary" onClick={onClose}>
            Dismiss
          </Button>
          <Button variant="primary" onClick={onReload}>
            Reload Latest Settings
          </Button>
        </div>
      }
    >
      <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
        To prevent overwriting newer updates, please reload the current configuration and apply your adjustments again.
      </p>
    </Dialog>
  );
};
