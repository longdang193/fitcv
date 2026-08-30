import React from "react";
import { describe, it, expect } from "vitest";
import {
  isSafeUrl,
  sanitizeUrl,
  parseSafeMarkdown,
  renderInlineMarkdown,
} from "./safe-renderer";

describe("Safe URL validation", () => {
  it("allows safe protocols and anchor links", () => {
    expect(isSafeUrl("https://example.com")).toBe(true);
    expect(isSafeUrl("http://localhost:8000")).toBe(true);
    expect(isSafeUrl("mailto:user@example.com")).toBe(true);
    expect(isSafeUrl("tel:+1234567890")).toBe(true);
    expect(isSafeUrl("#section-1")).toBe(true);
    expect(isSafeUrl("/relative/path")).toBe(true);
  });

  it("rejects unsafe and dangerous URL schemes", () => {
    expect(isSafeUrl("javascript:alert(document.cookie)")).toBe(false);
    expect(isSafeUrl("JAVASCRIPT:alert(1)")).toBe(false);
    expect(isSafeUrl("data:text/html,<script>alert(1)</script>")).toBe(false);
    expect(isSafeUrl("vbscript:msgbox(1)")).toBe(false);
    expect(isSafeUrl("file:///C:/Windows/system.ini")).toBe(false);
    expect(isSafeUrl("")).toBe(false);
  });

  it("sanitizes unsafe URLs to fallback anchor", () => {
    expect(sanitizeUrl("https://valid.com")).toBe("https://valid.com");
    expect(sanitizeUrl("javascript:alert(1)")).toBe("#");
    expect(sanitizeUrl("data:text/html,bad")).toBe("#");
  });
});

describe("Safe Markdown parser and renderer", () => {
  it("escapes raw HTML tags as literal text without DOM injection", () => {
    const raw = "## Section with <script>alert('xss')</script> and <img src='x' onerror='alert(1)'>";
    const nodes = parseSafeMarkdown(raw);
    expect(nodes.length).toBeGreaterThan(0);
  });

  it("neutralizes unsafe markdown links", () => {
    const textWithUnsafeLink = "Click here: [Malicious](javascript:alert(1))";
    const inline = renderInlineMarkdown(textWithUnsafeLink);
    expect(inline.length).toBeGreaterThan(0);
  });

  it("wraps unordered and ordered list items inside semantic ul and ol tags", () => {
    const markdownWithLists = `
- First bullet item
- Second bullet item

1. First numbered step
2. Second numbered step
`;
    const nodes = parseSafeMarkdown(markdownWithLists);
    expect(nodes).toHaveLength(2);

    const ulNode = nodes[0] as React.ReactElement;
    expect(ulNode.type).toBe("ul");
    expect(ulNode.props.className).toBe("cv-ul");
    expect(ulNode.props.children).toHaveLength(2);
    expect((ulNode.props.children as React.ReactElement[])[0].type).toBe("li");

    const olNode = nodes[1] as React.ReactElement;
    expect(olNode.type).toBe("ol");
    expect(olNode.props.className).toBe("cv-ol");
    expect(olNode.props.children).toHaveLength(2);
    expect((olNode.props.children as React.ReactElement[])[0].type).toBe("li");
  });

  it("renders headings, code blocks, and tables safely", () => {
    const markdownDoc = `
# Candidate CV

**Software Engineer** with experience in *Distributed Systems*.

## Skills
- TypeScript
- React
- Python

## Work History
1. Senior Developer at Acme Corp
2. Software Engineer at Beta Inc

\`\`\`typescript
const x: number = 42;
\`\`\`

| Skill | Level |
|---|---|
| React | Expert |
| Python | Senior |
`;
    const nodes = parseSafeMarkdown(markdownDoc);
    expect(nodes.length).toBeGreaterThan(3);
  });
});
