/**
 * Agent 도구 실행 결과. 종류에 따라 표현이 달라진다:
 *   execute_sql                   → 표 + 실행 SQL
 *   search_knowledge              → 출처 · 관련도 인용
 *   list_simulation/run_simulation → 핵심 수치 + 병목/제약 요약
 *   list_tables/describe_table/list_kpis/get_kpi → 참조한 지식 (기본 접힘)
 *
 * 구분은 카드가 아니라 얇은 좌측 룰 + 헤더 한 줄로 만든다.
 * 도구 목록은 Backend `agent/sdk_tools.py` 의 `TOOL_NAMES`를 기준으로 유지한다.
 */

import { useEffect, useState, type ReactNode } from "react";

import type { ToolResult } from "@/types/chat";
import { toolResultError } from "@/lib/tool-result";
import { ToolCall } from "@/components/assistant-ui/elements/tool-call";
import { CatalogResult } from "./tool-results/catalog-result";
import { catalogSummary } from "./tool-results/catalog-data";
import { DatabaseResult } from "./tool-results/database-result";
import { KnowledgeResult } from "./tool-results/knowledge-result";
import { SimulationResult } from "./tool-results/simulation-result";
import { asRecords, num, str } from "./tool-results/shared";

type Kind = "database" | "knowledge" | "simulation" | "catalog" | "generic";

const TOOL_META: Record<string, { label: string; kind: Kind }> = {
  execute_sql: { label: "데이터 조회", kind: "database" },
  search_knowledge: { label: "공정 문서 검색", kind: "knowledge" },
  list_simulation: { label: "시뮬레이션 목록", kind: "simulation" },
  run_simulation: { label: "시뮬레이션 실행", kind: "simulation" },
  list_tables: { label: "테이블 목록", kind: "catalog" },
  describe_table: { label: "테이블 상세", kind: "catalog" },
  list_kpis: { label: "KPI 목록", kind: "catalog" },
  get_kpi: { label: "KPI 정의", kind: "catalog" },
  list_recipes: { label: "집계 레시피 목록", kind: "catalog" },
  get_recipe: { label: "집계 레시피", kind: "catalog" },
  get_result_summary: { label: "결과 요약 조회", kind: "database" },
  get_result_page: { label: "결과 구간 조회", kind: "database" },
  prepare_table: { label: "표 준비", kind: "generic" },
  prepare_visualization: { label: "차트 준비", kind: "generic" },
};

function resolveKind(toolName: string, result?: ToolResult): { label: string; kind: Kind } {
  const meta = TOOL_META[toolName];
  const dataKind = result?.data ? str(result.data.kind) : null;
  if (meta) return meta;
  if (
    dataKind === "database" ||
    dataKind === "knowledge" ||
    dataKind === "simulation" ||
    dataKind === "catalog"
  ) {
    return { label: toolName || "도구 결과", kind: dataKind };
  }
  return { label: toolName || "도구 결과", kind: "generic" };
}

/**
 * 접힌 헤더에서도 결과의 핵심을 파악할 수 있도록 하는 한 줄 요약.
 * catalog 외 종류도 행 수 · 지표 수 · 문서 수를 보여준다(agent-workspace 요구:
 * "접힌 상태에서도 결과 종류, 상태, 행 수 또는 핵심 요약을 파악할 수 있어야 한다").
 */
function resultHeaderSummary(kind: Kind, data: Record<string, unknown>): string | null {
  if (kind === "catalog") return catalogSummary(data);
  if (kind === "database") {
    const rowCount = num(data.row_count);
    return rowCount !== null ? `${rowCount}행` : null;
  }
  if (kind === "simulation") {
    const kpis = asRecords(data.kpis);
    if (kpis.length > 0) return `지표 ${kpis.length}개`;
    const results = asRecords(data.results);
    return results.length > 0 ? `${results.length}건` : null;
  }
  if (kind === "knowledge") {
    const documents = asRecords(data.documents);
    return documents.length > 0 ? `문서 ${documents.length}건` : null;
  }
  return null;
}

export function ToolResultCard({
  toolName,
  args,
  result,
  running,
  messageRunning,
}: {
  toolName: string;
  args: Record<string, unknown>;
  result?: ToolResult;
  running: boolean;
  messageRunning: boolean;
}) {
  const { kind } = resolveKind(toolName, result);
  const data = result?.data ?? {};
  const errorText = result ? toolResultError(result) : null;

  const summary = resultHeaderSummary(kind, data);
  const unverified = kind === "catalog" && data.verified === false;
  const title = [toolName || "tool", summary].filter(Boolean).join(" · ");

  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!messageRunning) setOpen(false);
  }, [messageRunning]);

  return (
    <ToolCall
      label={unverified ? `${title} · 미검증` : title}
      error={errorText}
      running={running}
      incomplete={!result && !messageRunning}
      open={open}
      onOpenChange={setOpen}
    >
      <div className="flex flex-col gap-4">
        <DetailSection label="Parameters">
          <JsonDetail value={args} empty="파라미터가 없습니다." />
        </DetailSection>
        <DetailSection label="Result">
          {!result ? (
            <p className="text-ui text-ink-3">{messageRunning ? "Tool 결과를 기다리고 있습니다." : "결과가 도착하기 전에 실행이 종료되었습니다."}</p>
          ) : (
            <>
              {kind === "database" && <DatabaseResult data={data} />}
              {kind === "knowledge" && <KnowledgeResult data={data} />}
              {kind === "simulation" && <SimulationResult data={data} />}
              {kind === "catalog" && <CatalogResult data={data} />}
              {kind === "generic" && <GenericResult result={result} />}
            </>
          )}
        </DetailSection>
      </div>
    </ToolCall>
  );
}

function DetailSection({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section>
      <p className="mb-1.5 text-[10px] font-medium uppercase tracking-[0.08em] text-ink-3">{label}</p>
      {children}
    </section>
  );
}

function JsonDetail({ value, empty }: { value: Record<string, unknown>; empty: string }) {
  if (Object.keys(value).length === 0) return <p className="text-ui text-ink-3">{empty}</p>;
  return (
    <pre className="thin-scroll max-h-64 overflow-auto whitespace-pre-wrap break-words rounded bg-surface-2 p-3 font-mono text-data leading-relaxed text-ink-2">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function GenericResult({ result }: { result: ToolResult }) {
  if (result.data && Object.keys(result.data).length > 0) {
    return (
      <pre className="thin-scroll max-h-80 overflow-auto whitespace-pre-wrap break-words rounded bg-[#1c2530] p-3 font-mono text-data leading-relaxed text-[#d7dce4]">
        {JSON.stringify(result.data, null, 2)}
      </pre>
    );
  }
  if (result.content) {
    return (
      <p className="whitespace-pre-wrap break-words text-ui text-ink-2">
        {result.content}
      </p>
    );
  }
  return <p className="text-ui text-ink-3">결과 데이터가 없습니다.</p>;
}
