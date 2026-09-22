import type { FieldData, FieldGuide } from "@/types/knowledge";

/** 새 항목의 시작 값. 필수 필드만 채워 선택 필드가 빈 문자열로 저장되지 않게 한다. */
export function blankValue(field: Pick<FieldGuide, "widget" | "options" | "fields">): unknown {
  switch (field.widget) {
    case "boolean": return false;
    case "number": return 0;
    case "enum": return field.options?.[0] ?? "";
    case "string_list": case "record_list": return [];
    case "map": case "json": return {};
    case "object": return blankRecord(field.fields ?? []);
    default: return "";
  }
}
export const blankRecord = (fields: FieldGuide[]): FieldData => Object.fromEntries(fields.filter(f => f.required).map(f => [f.name, blankValue(f)]));
