export function parsePipelineResultTitleFilters(value: string): string[] {
  const values: string[] = [];
  const seen = new Set<string>();
  for (const part of value.split(/[\n,]/)) {
    const normalized = part.trim().replace(/\s+/g, " ");
    const key = normalized.toLocaleLowerCase();
    if (!normalized || seen.has(key)) continue;
    seen.add(key);
    values.push(normalized);
  }
  return values;
}
