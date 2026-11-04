export function parsePipelineResultTitleFilters(value: string): string[] {
  const values: string[] = [];
  const seen = new Set<string>();
  let quoteOpen = false;
  let start = 0;
  const parts: string[] = [];
  for (let index = 0; index < value.length; index += 1) {
    if (value[index] === '"' && value[index - 1] !== "\\") {
      quoteOpen = !quoteOpen;
    }
    if (!quoteOpen && (value[index] === "," || value[index] === "\n" || value[index] === "\r")) {
      parts.push(value.slice(start, index));
      start = index + 1;
    }
  }
  parts.push(value.slice(start));
  for (const part of parts) {
    const normalized = part.trim().replace(/\s+/g, " ");
    const key = normalized.toLocaleLowerCase();
    if (!normalized || seen.has(key)) continue;
    seen.add(key);
    values.push(normalized);
  }
  return values;
}
