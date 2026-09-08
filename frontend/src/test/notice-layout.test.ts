import { readFileSync } from "node:fs";
import { resolve } from "node:path";

describe("generic error notice layout", () => {
  it("keeps following content separated from error notices", () => {
    const css = readFileSync(resolve(__dirname, "../styles/main.css"), "utf8");
    expect(css).toMatch(/\.notice\.error\s*\{[^}]*margin-block-end:\s*16px;/s);
  });
});
