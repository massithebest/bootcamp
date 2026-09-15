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

import { useEffect, useState } from "react";

import type { ToolResult } from "@/types/chat";
import { toolResultError } from "@/lib/tool-result";
import {
  Tool,
  ToolContent,
  ToolHeader,
  ToolOutput,
} from "@/components/ai-elements/tool";
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
  prepare_visualization: { label: "차트 준비", kind: "generic" },
};

function resolveKind(result: ToolResult): { label: string; kind: Kind } {
  const meta = TOOL_META[result.toolName];
  const dataKind = result.data ? str(result.data.kind) : null;
  if (meta) return meta;
  if (
    dataKind === "database" ||
    dataKind === "knowledge" ||
    dataKind === "simulation" ||
    dataKind === "catalog"
  ) {
    return { label: result.toolName || "도구 결과", kind: dataKind };
  }
  return { label: result.toolName || "도구 결과", kind: "generic" };
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
  result,
  isRunning,
}: {
  result: ToolResult;
  /** 이 결과를 담은 assistant 메시지가 아직 실행 중인지. 실행 중에는 펼쳐서
   *  진행 상황을 보여주고, 끝나면 접어 최종 답변의 위계를 회복한다
   *  (AgentProgress와 동일한 open/touched 패턴). */
  isRunning: boolean;
}) {
  const { label, kind } = resolveKind(result);
  const data = result.data ?? {};
  const errorText = toolResultError(result);

  const summary = resultHeaderSummary(kind, data);
  const unverified = kind === "catalog" && data.verified === false;
  const title = [label, summary].filter(Boolean).join(" · ");

  // 분석 한 번에 지식(catalog) 조회가 4~6회 발생하므로 항상 접어 둔다.
  // 그 외 종류는 메시지가 실행 중일 때만 펼치고, 완료되면 접어 밀도를 되찾는다.
  const autoOpen = kind === "catalog" ? false : isRunning;
  const [open, setOpen] = useState(autoOpen);
  const [touched, setTouched] = useState(false);
  useEffect(() => {
    if (!touched) setOpen(autoOpen);
  }, [autoOpen, touched]);

  return (
    <Tool
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        setTouched(true);
      }}
      className="border-l border-line-strong pl-3"
    >
      <ToolHeader
        type={`tool-${result.toolName}`}
        state={errorText ? "output-error" : "output-available"}
        title={unverified ? `${title} · 미검증` : title}
      />
      <ToolContent>
        <ToolOutput
          errorText={errorText}
          output={
            <>
              {kind === "database" && <DatabaseResult data={data} />}
              {kind === "knowledge" && <KnowledgeResult data={data} />}
              {kind === "simulation" && <SimulationResult data={data} />}
              {kind === "catalog" && <CatalogResult data={data} />}
              {kind === "generic" && <GenericResult result={result} />}
            </>
          }
        />
      </ToolContent>
    </Tool>
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
