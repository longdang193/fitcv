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

  it("verifies 44x44px touch targets and accessible utility styles in main.css", () => {
    const fs = require("fs");
    const path = require("path");
    const mainCss = fs.readFileSync(path.resolve(__dirname, "../styles/main.css"), "utf-8");

    // .sr-only utility class exists
    expect(mainCss).toContain(".sr-only {");
    expect(mainCss).toContain("clip: rect(0, 0, 0, 0);");

    // Touch targets 44x44
    expect(mainCss).toContain(".mobile-menu-btn {");
    expect(mainCss).toContain("min-width: 44px;");
    expect(mainCss).toContain("min-height: 44px;");
    expect(mainCss).toContain(".btn-icon {");
    expect(mainCss).toContain("min-width: 44px;");
    expect(mainCss).toContain("min-height: 44px;");
    expect(mainCss).toContain(".switch {");
    expect(mainCss).toContain("min-width: 44px;");
    expect(mainCss).toContain("min-height: 44px;");

    // Coarse pointer touch target guarantees
    expect(mainCss).toContain("@media (pointer: coarse)");
    expect(mainCss).toContain(".switch");
    expect(mainCss).toContain(".tab-button");

    // Labelled table scroll cue and focus-visible
    expect(mainCss).toContain(".table-scroll:focus-visible");
    expect(mainCss).toContain("linear-gradient(to right, var(--surface)");

    // Danger button focus visible
    expect(mainCss).toContain(".btn-danger:focus-visible");

    // Zero-results state
    expect(mainCss).toContain(".zero-results-state");

    // Skip link
    expect(mainCss).toContain(".skip-link {");
    expect(mainCss).toContain(".skip-link:focus");

    // Dialog close and dismiss button 44px targets
    expect(mainCss).toContain(".dialog-close {");
    expect(mainCss).toContain(".notification-dismiss-btn");
    expect(mainCss).toContain(".toast-dismiss-btn");

    // Pipeline settings dialog responsive reflow at <= 640px (including 390px mobile)
    expect(mainCss).toContain("@media (max-width: 640px)");
    expect(mainCss).toContain("grid-template-columns: 1fr;");
    expect(mainCss).toContain("flex-direction: row;");

    // Semantic token reuse for status and console log levels
    expect(mainCss).toContain("background: var(--success-soft);");
    expect(mainCss).toContain(".console-level[data-level=\"error\"]");
    expect(mainCss).toContain("color: var(--danger);");
    expect(mainCss).toContain(".console-level[data-level=\"warning\"]");
    expect(mainCss).toContain("color: var(--warn);");

    // Compact action and rating button 44px touch targets and semantic token reuse
    expect(mainCss).toContain(".btn-compact::after");
    expect(mainCss).toContain(".small-action::after");
    expect(mainCss).toContain(".star-btn {");
    expect(mainCss).toContain("min-width: 44px;");
    expect(mainCss).toContain("min-height: 44px;");
    expect(mainCss).toContain(".star-btn[aria-pressed=\"true\"]");
    expect(mainCss).toContain("color: var(--warn);");

    // Sidebar brand block divider removed: preserves spacing without border-bottom
    const brandBlockMatch = mainCss.match(/\.brand\s*\{([^}]+)\}/);
    expect(brandBlockMatch).not.toBeNull();
    expect(brandBlockMatch![1]).not.toContain("border-bottom");
    expect(mainCss).toContain("border-right: 1px solid var(--border-soft);");
  });
});
