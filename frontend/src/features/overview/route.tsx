import React from "react";

export const OverviewPage: React.FC = () => {
  return (
    <div className="content-container">
      <div className="page-head" style={{ marginBottom: 24 }}>
        <p
          className="eyebrow"
          style={{
            color: "var(--accent)",
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            margin: "0 0 6px",
          }}
        >
          Personal FitCV
        </p>
        <h2
          style={{
            margin: 0,
            fontFamily: "var(--display-font)",
            fontSize: 26,
            letterSpacing: "-0.03em",
          }}
        >
          Overview
        </h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", fontSize: 13 }}>
          FitCV Local control plane and pipeline workspace.
        </p>
      </div>

      <div className="table-card" style={{ padding: 24 }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 16 }}>Welcome to FitCV Local</h3>
        <p style={{ margin: "0 0 16px", color: "var(--muted)", fontSize: 13 }}>
          The greenfield React/Vite/TypeScript frontend foundation is active. Use navigation to access workspace features.
        </p>
      </div>
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
