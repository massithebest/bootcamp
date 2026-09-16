import type { ReactNode } from "react";

const FIELD_LABELS: Record<string, string> = {
  table: "테이블",
  kpi_id: "KPI ID",
  recipe_id: "Recipe ID",
  scenario_id: "시나리오 ID",
  term: "용어",
  name: "이름",
  aliases: "별칭",
  description: "설명",
  definition: "정의",
  formula: "산식",
  grain: "데이터 기준",
  output_grain: "출력 기준",
  baseline: "기준값",
  shortfall_rule: "부족 판정 규칙",
  time_column: "시간 컬럼",
  tags: "태그",
  sources: "데이터 원천",
  columns: "컬럼",
  output_columns: "출력 컬럼",
  joins: "조인",
  caveats: "주의사항",
  query_rules: "조회 규칙",
  aggregation_rules: "집계 규칙",
  when_to_use: "사용 시점",
  visualization_hints: "시각화 안내",
  recipe_refs: "관련 Recipe",
  diagnostics: "진단 항목",
  sample_queries: "질문·SQL 예시",
  sql_template: "SQL 템플릿",
  cte_name: "CTE 이름",
  cte_sql: "CTE SQL",
  dataset: "데이터셋",
  question: "질문",
  steps: "실행 단계",
  expected: "기대 결과",
  table_counts: "테이블 건수",
  unmatched_rows: "미연결 건수",
  status: "검토 상태",
  owner: "담당자",
  updated: "수정일",
  source: "출처",
  type: "형식",
  desc: "설명",
  role: "역할",
  unit: "단위",
  ref: "참조",
  codes: "코드",
  hypothesis: "가설",
  how: "확인 방법",
  action: "작업",
  params: "입력값",
  expectation: "기대 결과",
  sql: "SQL",
};

const CHIP_COLLECTION_KEYS = new Set([
  "aliases",
  "grain",
  "output_grain",
  "recipe_refs",
  "sources",
  "tags",
]);
const SQL_KEYS = new Set(["cte_sql", "sql", "sql_template"]);
const IDENTIFIER_KEYS = new Set([
  "action",
  "cte_name",
  "dataset",
  "how",
  "kpi_id",
  "name",
  "recipe_id",
  "ref",
  "role",
  "scenario_id",
  "table",
  "term",
  "type",
  "unit",
]);

export function StructuredDetail({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) {
    return <p className="border-y border-line py-4 text-ui text-ink-2">표시할 상세 정보가 없습니다.</p>;
  }

  return (
    <dl data-slot="structured-detail" className="divide-y divide-line border-y border-line">
      {entries.map(([key, value]) => (
        <div key={key} className="grid gap-2 py-3 sm:grid-cols-[9rem_minmax(0,1fr)] sm:gap-4">
          <dt className="flex items-start gap-2 text-ui font-semibold text-ink-2">
            <span>{fieldLabel(key)}</span>
            {Array.isArray(value) && value.length > 0 && (
              <span className="shrink-0 font-mono text-2xs font-normal tabular-nums text-ink-2">
                {value.length.toLocaleString("ko-KR")}개
              </span>
            )}
          </dt>
          <dd className="min-w-0">
            <StructuredValue fieldKey={key} value={value} />
          </dd>
        </div>
      ))}
    </dl>
  );
}

function StructuredValue({ fieldKey, value }: { fieldKey: string; value: unknown }): ReactNode {
  if (value === null || value === undefined || value === "") return <EmptyValue />;

  if (typeof value === "string") {
    if (SQL_KEYS.has(fieldKey)) {
      return (
        <pre className="thin-scroll max-h-96 overflow-auto whitespace-pre-wrap break-words border-l-2 border-line-strong bg-surface px-3 py-2 font-mono text-data leading-relaxed text-ink">
          {value}
        </pre>
      );
    }
    const statusLabel = value === "verified" ? "검토 완료" : value === "draft" ? "미검토" : null;
    if (statusLabel) return <span className="text-ui text-ink">{statusLabel}</span>;
    if (IDENTIFIER_KEYS.has(fieldKey)) {
      return <code className="break-words font-mono text-data text-ink">{value}</code>;
    }
    return <p className="whitespace-pre-wrap break-words text-ui leading-relaxed text-ink">{value}</p>;
  }

  if (typeof value === "number") {
    return <span className="font-mono text-data tabular-nums text-ink">{value.toLocaleString("ko-KR")}</span>;
  }
  if (typeof value === "boolean") return <span className="text-ui text-ink">{value ? "예" : "아니요"}</span>;

  if (Array.isArray(value)) {
    if (value.length === 0) return <EmptyValue />;
    if (fieldKey === "sample_queries" && isSqlQueryExamples(value)) {
      return <SqlExamples samples={value} />;
    }
    if ((fieldKey === "columns" || fieldKey === "output_columns") && value.every(isRecord)) {
      return <ColumnList columns={value} />;
    }
    if (value.every(isPrimitive)) {
      return CHIP_COLLECTION_KEYS.has(fieldKey)
        ? <ChipCollection values={value} />
        : <TextList values={value} />;
    }
    if (value.every(isRecord)) return <RecordList records={value} />;
    return <ValueList fieldKey={fieldKey} values={value} />;
  }

  if (isRecord(value)) return <RecordFields data={value} />;
  return <EmptyValue />;
}

function ChipCollection({ values }: { values: (string | number | boolean | null)[] }) {
  return (
    <ul className="flex flex-wrap gap-2">
      {values.map((value, index) => (
        <li key={`${String(value)}:${index}`} className="rounded bg-surface-2 px-2 py-1 font-mono text-data text-ink-2">
          {displayPrimitive(value)}
        </li>
      ))}
    </ul>
  );
}

function TextList({ values }: { values: (string | number | boolean | null)[] }) {
  return (
    <ul className="space-y-2 text-ui leading-relaxed text-ink">
      {values.map((value, index) => (
        <li key={`${String(value)}:${index}`} className="flex min-w-0 items-start gap-2">
          <span aria-hidden className="mt-2 size-1.5 shrink-0 rounded-full bg-line-strong" />
          <span className="min-w-0 whitespace-pre-wrap break-words">{displayPrimitive(value)}</span>
        </li>
      ))}
    </ul>
  );
}

function ColumnList({ columns }: { columns: Record<string, unknown>[] }) {
  return (
    <ul className="divide-y divide-line border-y border-line">
      {columns.map((column, index) => {
        const name = displayPrimitive(column.name ?? `column_${index + 1}`);
        const description = column.desc;
        const badges = [column.type, column.role, column.unit].filter(isPresentPrimitive);
        const rest = Object.fromEntries(
          Object.entries(column).filter(([key, value]) =>
            !["name", "desc", "type", "role", "unit"].includes(key) && hasContent(value),
          ),
        );
        return (
          <li key={`${name}:${index}`} className="border-l-2 border-line py-3 pl-3 first:pt-2 last:pb-2">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <code className="break-words font-mono text-data font-semibold text-ink">{name}</code>
              {badges.map((badge, badgeIndex) => (
                <span key={`${String(badge)}:${badgeIndex}`} className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-2xs text-ink-2">
                  {displayPrimitive(badge)}
                </span>
              ))}
            </div>
            {isPresentPrimitive(description) && (
              <p className="mt-1 whitespace-pre-wrap break-words text-ui leading-relaxed text-ink-2">
                {displayPrimitive(description)}
              </p>
            )}
            {Object.keys(rest).length > 0 && <div className="mt-2"><RecordFields data={rest} compact /></div>}
          </li>
        );
      })}
    </ul>
  );
}

function RecordList({ records }: { records: Record<string, unknown>[] }) {
  return (
    <ol className="divide-y divide-line border-y border-line">
      {records.map((record, index) => (
        <li key={index} className="grid grid-cols-[1.5rem_minmax(0,1fr)] gap-2 py-3 first:pt-2 last:pb-2">
          <span className="font-mono text-2xs tabular-nums text-ink-2">{index + 1}</span>
          <RecordFields data={record} compact />
        </li>
      ))}
    </ol>
  );
}

function ValueList({ fieldKey, values }: { fieldKey: string; values: unknown[] }) {
  return (
    <ol className="divide-y divide-line border-y border-line">
      {values.map((value, index) => (
        <li key={index} className="grid grid-cols-[1.5rem_minmax(0,1fr)] gap-2 py-3 first:pt-2 last:pb-2">
          <span className="font-mono text-2xs tabular-nums text-ink-2">{index + 1}</span>
          <div className="min-w-0"><StructuredValue fieldKey={fieldKey} value={value} /></div>
        </li>
      ))}
    </ol>
  );
}

function RecordFields({ data, compact = false }: { data: Record<string, unknown>; compact?: boolean }) {
  return (
    <dl className={compact ? "space-y-2" : "divide-y divide-line border-l-2 border-line pl-3"}>
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="grid min-w-0 gap-1 sm:grid-cols-[7rem_minmax(0,1fr)] sm:gap-3">
          <dt className="text-2xs font-semibold text-ink-2">{fieldLabel(key)}</dt>
          <dd className="min-w-0"><StructuredValue fieldKey={key} value={value} /></dd>
        </div>
      ))}
    </dl>
  );
}

function SqlExamples({ samples }: { samples: { question: string; sql: string }[] }) {
  return (
    <div className="space-y-3">
      {samples.map((sample, index) => (
        <article key={`${sample.question}:${index}`} className="border-l-2 border-line-strong bg-surface px-3 py-3">
          <p className="text-2xs font-semibold text-ink-2">질문 {samples.length > 1 ? index + 1 : ""}</p>
          <p className="mt-1 whitespace-pre-wrap break-words text-ui leading-relaxed text-ink">{sample.question}</p>
          <p className="mt-3 text-2xs font-semibold text-ink-2">SQL</p>
          <pre className="thin-scroll mt-1 max-h-96 overflow-auto whitespace-pre-wrap break-words border-l-2 border-line-strong bg-canvas px-3 py-2 font-mono text-data leading-relaxed text-ink">{sample.sql}</pre>
        </article>
      ))}
    </div>
  );
}

function EmptyValue() {
  return <span className="text-ui text-ink-2">없음</span>;
}

function fieldLabel(key: string): string {
  return FIELD_LABELS[key] ?? key.replaceAll("_", " ");
}

function displayPrimitive(value: unknown): string {
  if (value === null || value === undefined || value === "") return "없음";
  if (typeof value === "boolean") return value ? "예" : "아니요";
  if (typeof value === "number") return value.toLocaleString("ko-KR");
  return String(value);
}

function isPrimitive(value: unknown): value is string | number | boolean | null {
  return value === null || ["string", "number", "boolean"].includes(typeof value);
}

function isPresentPrimitive(value: unknown): value is string | number | boolean {
  return isPrimitive(value) && value !== null && value !== "";
}

function hasContent(value: unknown): boolean {
  if (value === null || value === undefined || value === "") return false;
  if (Array.isArray(value)) return value.length > 0;
  if (isRecord(value)) return Object.keys(value).length > 0;
  return true;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isSqlQueryExamples(value: unknown): value is { question: string; sql: string }[] {
  return Array.isArray(value) && value.every(item => isRecord(item) && typeof item.question === "string" && typeof item.sql === "string");
}
