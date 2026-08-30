import { describe, it, expect } from "vitest";

declare function require(module: string): any;
declare const __dirname: string;

describe("accessibility and design token compliance", () => {
  it("enforces color-scheme, semantic tokens, and reduced-motion reset in CSS", () => {
    const fs = require("fs");
    const path = require("path");

    const tokensPath = path.resolve(__dirname, "../styles/tokens.css");
    const mainPath = path.resolve(__dirname, "../styles/main.css");

    const tokensCss = fs.readFileSync(tokensPath, "utf-8");
    const mainCss = fs.readFileSync(mainPath, "utf-8");

    // Tokens check
    expect(tokensCss).toContain("color-scheme: light;");
    expect(tokensCss).toContain("color-scheme: dark;");
    expect(tokensCss).toContain("--accent:");
    expect(tokensCss).toContain("--focus-ring:");
    expect(tokensCss).toContain("--radius-md:");

    // Accessibility check
    expect(mainCss).toContain(":focus-visible");
    expect(mainCss).toContain("prefers-reduced-motion: reduce");
    expect(mainCss).toContain("min-height: 44px");
  });
});
