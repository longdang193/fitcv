import React from "react";
import { createRoot } from "react-dom/client";
import { AppShell } from "./app/app-shell";
import "./styles/main.css";

const rootElement = document.getElementById("root");
if (rootElement) {
  const root = createRoot(rootElement);
  root.render(
    <React.StrictMode>
      <AppShell />
    </React.StrictMode>
  );
}
