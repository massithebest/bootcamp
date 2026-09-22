/** `done.data.suggestions` 검증. 엄격한 형식이 아니면 후속질문을 표시하지 않는다(추측·보정하지 않는다). */
export const SUGGESTION_MIN = 2;
export const SUGGESTION_MAX = 4;
export const SUGGESTION_MAX_LENGTH = 120;

export function parseSuggestions(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const seen = new Set<string>();
  const items: string[] = [];
  for (const raw of value) {
    if (typeof raw !== "string") return undefined;
    const text = raw.trim();
    if (!text || text.length > SUGGESTION_MAX_LENGTH) return undefined;
    if (!seen.has(text)) {
      seen.add(text);
      items.push(text);
    }
  }
  return items.length >= SUGGESTION_MIN && items.length <= SUGGESTION_MAX ? items : undefined;
}
