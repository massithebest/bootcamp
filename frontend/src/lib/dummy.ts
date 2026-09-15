/**
 * 초기 화면용 SMT2020 benchmark 예시 데이터.
 * 수치는 원본을 변환한 SQLite 조회 및 입력 정합성 mock 결과만 사용한다.
 */

import type { ChatMessage } from "@/types/chat";
import type {
  CurrentUser,
  Session,
  SessionMetadata,
  SystemPromptState,
} from "@/types/workspace";

export const CURRENT_USER: CurrentUser = {
  name: "손흥민",
  team: "생산관리팀 · 계획파트",
};

export const SESSIONS: Session[] = [
  { id: "s-0901", title: "LVHM 제품별 초기 WIP", lastActivity: "방금 전", group: "today", traces: ["query", "simulation"] },
  { id: "s-0902", title: "part_1 Route 확인", lastActivity: "오늘 11:05", group: "today", traces: ["query"] },
  { id: "s-0903", title: "Dry Etch 설비 수량", lastActivity: "3일 전", group: "week", traces: ["query"] },
  { id: "s-0904", title: "HVLM 납기 우선 Lot", lastActivity: "5일 전", group: "week", traces: ["query"] },
  { id: "s-0905", title: "제품별 공정 Step 수", lastActivity: "6일 전", group: "week", traces: ["query"] },
  { id: "s-0906", title: "SMT2020 입력 관계 검증", lastActivity: "3주 전", group: "earlier", traces: ["simulation"] },
];

export const SESSION_METADATA: SessionMetadata = {
  model: "claude-sonnet-4",
  toolCallCount: 4,
  lastResponseSeconds: 2.1,
  avgResponseSeconds: 2.4,
  dataAsOf: "SMT2020 공개 benchmark · 시작 시점 2018-01-01",
  simulationServer: { status: "ok", label: "입력 정합성 Mock" },
};

export const SYSTEM_PROMPT: SystemPromptState = {
  content: `당신은 SMT2020 반도체 FAB benchmark를 조회하는 생산계획 에이전트다.

역할:
- 제품, Route, 공정 Step, 설비 Family, 초기 WIP와 신규 Lot 투입 정보를 조회한다.
- SQL과 입력 검증 Mock의 근거 수치를 함께 제시한다.

원칙:
- 질의 대상 dataset을 HVLM 또는 LVHM으로 먼저 확정한다.
- 여러 테이블을 JOIN할 때 업무 키와 dataset을 함께 사용한다.
- 데이터에 없는 completion, throughput, 병목, 납기 달성률을 추정하지 않는다.
- 입력 검증 Mock을 실제 이산사건 시뮬레이션 결과로 표현하지 않는다.`,
  revisions: [
    {
      version: "v1",
      editedAt: "2026-09-15 21:00",
      editedBy: "손흥민",
      note: "SMT2020 SQLite와 입력 정합성 Mock 기준으로 전환",
    },
  ],
};

export const EXAMPLE_QUESTIONS: string[] = [
  "LVHM에서 제품별 초기 WIP Lot과 piece 수를 조회해줘.",
  "LVHM part_1의 공정 Route를 순서대로 보여줘.",
  "HVLM의 Dry Etch 설비는 Family별로 몇 대 있어?",
  "LVHM 제품별 전체 공정 Step 수를 알려줘.",
  "HVLM에서 납기가 가장 빠른 WIP와 신규 투입 Lot을 보여줘.",
  "SMT2020 LVHM 입력 테이블의 관계를 검증해줘.",
];

/** 초기 로드 시 보여줄 benchmark 기반 대화. */
export const SEED_CONVERSATION: ChatMessage[] = [
  {
    id: "seed-u1",
    role: "user",
    content: "SMT2020 LVHM에서 제품별 초기 WIP를 조회하고 입력 관계도 검증해줘.",
    parts: [],
    statuses: [],
    runState: { type: "complete" },
  },
  {
    id: "seed-a1",
    role: "assistant",
    content: "",
    runState: { type: "complete" },
    statuses: [
      { step: "plan", label: "질의 분석", status: "completed" },
      { step: "get_kpi", label: "초기 WIP 정의 확인", status: "completed" },
      { step: "execute_sql", label: "제품별 초기 WIP 조회", status: "completed" },
      { step: "run_simulation", label: "SMT2020 입력 관계 검증", status: "completed" },
      { step: "prepare_visualization", label: "제품별 WIP 차트 준비", status: "completed" },
    ],
    parts: [
      {
        kind: "tool" as const,
        id: "seed-sql",
        result: {
          id: "seed-sql",
          toolName: "execute_sql",
          content: null,
          data: {
            status: "ok",
            kind: "database",
            type: "inline",
            purpose: "LVHM 제품별 초기 WIP Lot과 piece 수",
            row_count: 10,
            sql: "SELECT part, COUNT(*) AS lot_count, SUM(pieces) AS piece_count\nFROM wip\nWHERE dataset = 'LVHM'\nGROUP BY part\nORDER BY part;",
            table: {
              columns: ["part", "lot_count", "piece_count"],
              rows: [
                ["part_1", 274, 6850], ["part_10", 211, 5275],
                ["part_2", 280, 7000], ["part_3", 310, 7750],
                ["part_4", 179, 4475], ["part_5", 129, 3225],
                ["part_6", 167, 4175], ["part_7", 190, 4750],
                ["part_8", 209, 5225], ["part_9", 207, 5175],
              ],
            },
          },
        },
      },
      {
        kind: "tool" as const,
        id: "seed-simulation",
        result: {
          id: "seed-simulation",
          toolName: "run_simulation",
          content: null,
          data: {
            status: "ok",
            kind: "simulation",
            type: "inline",
            scenario: "SMT2020 LVHM 입력 검증",
            kpis: [
              { label: "Part", value: 10, unit: "개", tone: "ok" },
              { label: "Route Step", value: 4013, unit: "개", tone: "ok" },
              { label: "Tool Family", value: 106, unit: "개", tone: "ok" },
              { label: "초기 WIP", value: 2156, unit: "lot", tone: "ok" },
            ],
            summary: "모든 핵심 입력 관계가 유효합니다. 이 결과는 실제 이산사건 시뮬레이션이 아닌 SMT2020 입력 정합성 mock입니다.",
            results: [
              { check: "part_to_route_step", source_rows: 10, matched_rows: 10, unmatched_rows: 0 },
              { check: "route_step_to_tool", source_rows: 4013, matched_rows: 4013, unmatched_rows: 0 },
              { check: "wip_to_part", source_rows: 2156, matched_rows: 2156, unmatched_rows: 0 },
              { check: "orders_to_part", source_rows: 21, matched_rows: 21, unmatched_rows: 0 },
              { check: "wip_curstep_to_route_step", source_rows: 2156, matched_rows: 2156, unmatched_rows: 0 },
            ],
            table: {
              columns: ["table", "row_count"],
              rows: [
                ["part", 10], ["route_step", 4013], ["tool", 106],
                ["orders", 21], ["wip", 2156], ["setup", 13],
                ["setup_group", 9], ["down_calendar", 11],
                ["pm_calendar", 292], ["calendar_attach", 303], ["transport", 1],
              ],
            },
          },
        },
      },
      {
        kind: "text" as const,
        id: "seed-final",
        text:
          "## 확인 결과\n\n" +
          "SMT2020 `LVHM`의 초기 WIP는 **2,156 lot**이며 10개 Part에 분포합니다. " +
          "입력 검증 Mock에서 Part→Route, Route Step→Tool, WIP/Order→Part와 현재 Step 관계의 미연결 건수는 모두 0건입니다.\n\n" +
          "이 결과는 입력 데이터의 구조와 관계를 확인한 것이며 실제 생산 완료량이나 병목을 예측한 이산사건 시뮬레이션 결과는 아닙니다.",
      },
    ],
  },
];
