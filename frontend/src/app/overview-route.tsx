import React, { useState } from "react";
import { Button } from "../components";
import { PipelineSettingsDialog } from "../features/pipeline-settings/pipeline-settings-dialog";

export function isExplicitOfflineOrMock(explicitFlag?: boolean): boolean {
  if (explicitFlag) return true;
  if (typeof window !== "undefined") {
    if ((window as any).__FITCV_MOCK__ || (window as any).__FITCV_OFFLINE__) return true;
    const search = window.location?.search || "";
    if (search.includes("mock=true") || search.includes("offline=true")) return true;
  }
  return false;
}

export interface OverviewPageProps {
  allowOfflineFallback?: boolean;
}

export const OverviewPage: React.FC<OverviewPageProps> = () => {
  const [isPipelineDialogOpen, setIsPipelineDialogOpen] = useState(false);

  return (
    <div className="content-container overview-page">
      {/* Page Header */}
      <div className="page-head">
        <div>
          <p className="eyebrow">Pipeline</p>
          <h2>Overview</h2>
          <p>Set the most important pipeline volumes and output limits. Changes apply to future runs.</p>
        </div>
        <div className="overview-actions">
          <Button variant="primary" onClick={() => setIsPipelineDialogOpen(true)}>
            Pipeline Settings
          </Button>
        </div>
      </div>

      {/* Before your first run - Onboarding Card */}
      <section className="section-card start-here" aria-labelledby="start-here-title">
        <div className="start-here-head">
          <div>
            <p className="eyebrow">Normal use</p>
            <h3 id="start-here-title">Before your first run</h3>
            <p>Confirm a candidate profile, bring in jobs, and connect a model. Technical tuning below is optional.</p>
          </div>
        </div>
        <ol className="start-here-list">
          <li className="start-here-step">
            <a href="#/candidate-profile">Confirm Candidate Profile</a>
            <span>Review source-backed facts before matching.</span>
          </li>
          <li className="start-here-step">
            <a href="#/scans">Bring in jobs</a>
            <span>Scan supported companies or add job input from Runs.</span>
          </li>
          <li className="start-here-step">
            <a href="#/settings/api-providers">Connect a model</a>
            <span>Validate one provider before AI-assisted stages run.</span>
          </li>
        </ol>
      </section>

      {/* Settings Sections */}
      <PipelineSettingsDialog
        open={isPipelineDialogOpen}
        onClose={() => setIsPipelineDialogOpen(false)}
      />
    </div>
  );
};

export const route = {
  id: "overview",
  path: "#/overview",
  title: "Overview",
  group: "workspace" as const,
  order: 10,
  component: OverviewPage,
};

export default route;
