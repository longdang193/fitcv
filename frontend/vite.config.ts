import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

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
    port: 5173,
    proxy: {
      "/api-providers": "http://127.0.0.1:8000",
      "/llm-configuration": "http://127.0.0.1:8000",
      "/prompt-configurations": "http://127.0.0.1:8000",
      "/system-settings": "http://127.0.0.1:8000",
      "/settings": "http://127.0.0.1:8000",
      "/local": "http://127.0.0.1:8000",
      "/runs": "http://127.0.0.1:8000",
      "/scans": "http://127.0.0.1:8000",
      "/tracked-companies": "http://127.0.0.1:8000",
      "/candidate-profiles": "http://127.0.0.1:8000",
      "/candidate-profile-creation-attempts": "http://127.0.0.1:8000",
      "/candidate-profile-field-schema": "http://127.0.0.1:8000",
      "/bookmarks": "http://127.0.0.1:8000",
      "/synonym-policies": "http://127.0.0.1:8000",
      "/synonym-suggestions": "http://127.0.0.1:8000",
      "/synonym-processing-runs": "http://127.0.0.1:8000",
      "/personalization": "http://127.0.0.1:8000",
      "/healthz": "http://127.0.0.1:8000",
    },
  },
});
