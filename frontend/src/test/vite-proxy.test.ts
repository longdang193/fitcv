import { describe, expect, it } from "vitest";
import config from "../../vite.config";

describe("Vite API proxy", () => {
  it("proxies catalog discovery and Track requests to backend", () => {
    const proxy = (config as { server?: { proxy?: Record<string, unknown> } }).server?.proxy;
    expect(proxy).toHaveProperty("/company-catalog");
  });

  it("proxies CV preview and download requests at /cv-versions", () => {
    const proxy = (config as { server?: { proxy?: Record<string, any> } }).server?.proxy || {};
    expect(proxy).toHaveProperty("/cv-versions");
    expect(proxy["/cv-versions"]).toBe("http://127.0.0.1:8000");
  });
});
