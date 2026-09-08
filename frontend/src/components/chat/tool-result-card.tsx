/**
 * Agent 도구 실행 결과. 종류에 따라 표현이 달라진다:
 *   query_database                → 표 + 실행 SQL
 *   search_knowledge              → 출처 · 관련도 인용
 *   simulate_*                    → 핵심 수치 + 병목/제약 요약
 *
 * 구분은 카드가 아니라 얇은 좌측 룰 + 헤더 한 줄로 만든다.
 */

"use client";

import type { ToolResult } from "@/types/chat";
import { DatabaseResult } from "./tool-results/database-result";
import { KnowledgeResult } from "./tool-results/knowledge-result";
import { SimulationResult } from "./tool-results/simulation-result";
import { str } from "./tool-results/shared";

type Kind = "database" | "knowledge" | "simulation" | "generic";

const TOOL_META: Record<string, { label: string; kind: Kind }> = {
  query_database: { label: "생산 실적 조회", kind: "database" },
  search_knowledge: { label: "공정 문서 검색", kind: "knowledge" },
  simulate_line_capacity: {
    label: "라인 생산량 시뮬레이션",
    kind: "simulation",
  },
  simulate_material_constraint: {
    label: "자재 제약 시뮬레이션",
    kind: "simulation",
  },
  simulate_line_comparison: {
    label: "라인 비교 시뮬레이션",
    kind: "simulation",
  },
};

function resolveKind(result: ToolResult): { label: string; kind: Kind } {
  const meta = TOOL_META[result.toolName];
  const dataKind = result.data ? str(result.data.kind) : null;
  if (meta) return meta;
  if (dataKind === "database" || dataKind === "knowledge" || dataKind === "simulation") {
    return { label: result.toolName || "도구 결과", kind: dataKind };
  }
  return { label: result.toolName || "도구 결과", kind: "generic" };
}

export function ToolResultCard({ result }: { result: ToolResult }) {
  const { label, kind } = resolveKind(result);
  const data = result.data ?? {};

  return (
    <section className="border-l border-line-strong pl-3">
      <header className="mb-2 flex items-baseline gap-2">
        <h3 className="text-2xs font-semibold text-ink-2">{label}</h3>
        <span className="font-mono text-2xs text-ink-3">{result.toolName}</span>
      </header>
      {kind === "database" && <DatabaseResult data={data} />}
      {kind === "knowledge" && <KnowledgeResult data={data} />}
      {kind === "simulation" && <SimulationResult data={data} />}
      {kind === "generic" && <GenericResult result={result} />}
    </section>
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
