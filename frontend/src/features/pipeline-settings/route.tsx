import React, { useState } from "react";
import { Button } from "../../components";
import { PipelineSettingsDialog } from "./pipeline-settings-dialog";
import { FeatureRoute } from "../../app/route-registry";

export const PipelineSettingsPage: React.FC = () => {
  const [dialogOpen, setDialogOpen] = useState(true);

  return (
    <div className="content-container" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="page-head">
        <div>
          <p className="eyebrow">Pipeline</p>
          <h2>Pipeline Settings</h2>
          <p>Configure pipeline stages, limits, criteria, and automation rules.</p>
        </div>
        <div>
          <Button variant="primary" onClick={() => setDialogOpen(true)}>
            Open Pipeline Settings
          </Button>
        </div>
      </div>

      <PipelineSettingsDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
      />
    </div>
  );
};

export const route: FeatureRoute = {
  id: "pipeline-settings",
  path: "#/settings/pipeline",
  title: "Pipeline Settings",
  group: "settings",
  order: 25,
  component: PipelineSettingsPage,
};

export default route;
