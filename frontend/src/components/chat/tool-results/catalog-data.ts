import { asRecord, asRecords, str } from "./shared";

export type CatalogType = "table" | "kpi" | "table_list" | "kpi_list" | "recipe" | "recipe_list";

export function catalogTypeOf(v: unknown): CatalogType | null {
  return v === "table" || v === "kpi" || v === "table_list" || v === "kpi_list" || v === "recipe" || v === "recipe_list"
    ? v
    : null;
}

/** 헤더에 붙일 한 줄 요약. 카드를 펼치지 않아도 무엇을 참조했는지 보이게 한다. */
export function catalogSummary(data: Record<string, unknown>): string | null {
  const type = catalogTypeOf(data.catalog_type);
  if (!type) return null;

  const payload = data.data;

  if (type === "table") {
    return str(asRecord(payload).table);
  }
  if (type === "kpi" || type === "recipe") {
    return str(asRecord(payload).name);
  }
  return `${asRecords(payload).length}건`;
}
