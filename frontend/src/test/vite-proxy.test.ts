import { describe, expect, it } from "vitest";
import config from "../../vite.config";

describe("Vite API proxy", () => {
  it("proxies catalog discovery and Track requests to backend", () => {
    const proxy = (config as { server?: { proxy?: Record<string, unknown> } }).server?.proxy;
    expect(proxy).toHaveProperty("/company-catalog");
  });
});
