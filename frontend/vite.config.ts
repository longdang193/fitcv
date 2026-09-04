import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import devServerConfig from "../config/dev-server.json";

const apiOrigin = `http://${devServerConfig.host}:${devServerConfig.backendPort}`;
const apiPaths = [
  "/api-providers",
  "/llm-configuration",
  "/prompt-configurations",
  "/system-settings",
  "/settings",
  "/local",
  "/runs",
  "/scans",
  "/tracked-companies",
  "/candidate-profiles",
  "/candidate-profile-creation-attempts",
  "/candidate-profile-field-schema",
  "/bookmarks",
  "/synonym-policies",
  "/synonym-suggestions",
  "/synonym-processing-runs",
  "/personalization",
  "/healthz",
];

export default defineConfig({
  plugins: [react()],
  base: "/app/",
  resolve: {
    alias: {
      "@": new URL("./src", import.meta.url).pathname,
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    host: devServerConfig.host,
    port: devServerConfig.frontendPort,
    proxy: Object.fromEntries(apiPaths.map((path) => [path, apiOrigin])),
  },
});
