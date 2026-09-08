/**
 * 하드코딩된 더미 데이터.  실제 DB / History / Skills 연동은 아직 없다.
 * 제조 생산계획 도메인의 실제 어휘로 채운다 (로렘 입숨 / "샘플 1" 금지).
 */

import type { ChatMessage } from "@/types/chat";
import type {
  CurrentUser,
  Session,
  SessionMetadata,
  Skill,
  SystemPromptState,
} from "@/types/workspace";

export const CURRENT_USER: CurrentUser = {
  name: "손흥민",
  team: "생산관리팀 · 계획파트",
};

export const SESSIONS: Session[] = [
  {
    id: "s-0901",
    title: "9월 A라인 목표 달성 검토",
    lastActivity: "방금 전",
    group: "today",
    traces: ["query", "simulation"],
  },
  {
    id: "s-0902",
    title: "SMT 자재 부족 대응",
    lastActivity: "오늘 11:05",
    group: "today",
    traces: ["query", "document", "simulation"],
  },
  {
    id: "s-0903",
    title: "10월 라인별 효율 비교",
    lastActivity: "3일 전",
    group: "week",
    traces: ["simulation"],
  },
  {
    id: "s-0904",
    title: "B라인 납기 지연 원인 분석",
    lastActivity: "5일 전",
    group: "week",
    traces: ["query", "document"],
  },
  {
    id: "s-0905",
    title: "생산계획 수립 기준 문의",
    lastActivity: "6일 전",
    group: "week",
    traces: ["document"],
  },
  {
    id: "s-0906",
    title: "8월 자재 소요량 재산정",
    lastActivity: "3주 전",
    group: "earlier",
    traces: ["query", "simulation"],
  },
  {
    id: "s-0907",
    title: "C라인 신규 품목 투입 검토",
    lastActivity: "1개월 전",
    group: "earlier",
    traces: ["document", "simulation"],
  },
];

export const SKILLS: Skill[] = [
  {
    toolName: "query_database",
    label: "생산 실적 조회",
    description: "MES · ERP 생산 실적, 가동률, 재고, 소요량을 조회",
    enabled: true,
    lastCalledAt: "오늘 14:21",
  },
  {
    toolName: "search_knowledge",
    label: "공정 문서 검색",
    description: "공정 표준서, 작업 지시, 품질 기준 문서 검색",
    enabled: true,
    lastCalledAt: "어제 17:40",
  },
  {
    toolName: "simulate_line_capacity",
    label: "라인 생산량 시뮬레이션",
    description: "공정별 처리량 · 가동 시간 기준 최대 생산 가능 수량 산출",
    enabled: true,
    lastCalledAt: "오늘 14:22",
  },
  {
    toolName: "simulate_material_constraint",
    label: "자재 제약 시뮬레이션",
    description: "자재 재고 · 입고 예정 기준 생산 가능 수량과 부족분 산출",
    enabled: true,
    lastCalledAt: "3일 전",
  },
  {
    toolName: "simulate_line_comparison",
    label: "라인 비교 시뮬레이션",
    description: "복수 라인 · 시나리오의 달성률과 리드타임 비교",
    enabled: false,
    lastCalledAt: "1주 전",
  },
];

export const SESSION_METADATA: SessionMetadata = {
  model: "claude-sonnet-4",
  toolCallCount: 4,
  lastResponseSeconds: 8.2,
  avgResponseSeconds: 6.4,
  dataAsOf: "2026-09-07 23:00 MES 마감 기준",
  simulationServer: { status: "ok", label: "정상 · 응답 120ms" },
};

export const SYSTEM_PROMPT: SystemPromptState = {
  content: `당신은 제조 현장의 생산계획을 지원하는 에이전트다.

역할:
- 계획 담당자의 자연어 질문에 대해 생산 실적 조회, 공정 문서 검색,
  라인/자재/비교 시뮬레이션 중 필요한 것을 선택해 실행한다.
- 답변에는 항상 근거(조회 결과, 참조 문서, 시뮬레이션 수치)를 함께 제시한다.
- 달성 가능 여부는 "가능 / 조건부 가능 / 불가"로 구분하고 조건을 명시한다.

원칙:
- 데이터에 없는 수치를 추정하지 않는다. 불확실하면 불확실하다고 말한다.
- 자재 기준일자와 MES 마감 시각을 답변에 함께 밝힌다.
- 병목 공정과 제약 자재를 항상 식별한다.`,
  revisions: [
    {
      version: "v5",
      editedAt: "2026-09-05 09:12",
      editedBy: "손흥민",
      note: "자재 기준일자 명시 규칙 추가",
    },
    {
      version: "v4",
      editedAt: "2026-08-21 14:30",
      editedBy: "이재훈",
      note: "달성 여부 3단계 구분 도입",
    },
    {
      version: "v3",
      editedAt: "2026-08-02 10:05",
      editedBy: "손흥민",
      note: "병목 공정 식별 의무화",
    },
  ],
};

export const EXAMPLE_QUESTIONS: string[] = [
  "9월 A라인에서 품목 KRA-1180을 1,000개 생산 가능한가? 자재 제약도 같이 봐줘.",
  "SMT 3라인 가동률이 지난주 대비 얼마나 떨어졌고 원인이 뭔가?",
  "10월 자재 MDF-0563 제약을 고려하면 라인별 최대 생산량은?",
  "B라인과 D라인 중 납기를 2주 단축하는 데 유리한 쪽은?",
];

/** 초기 로드 시 보여줄 더미 대화 (세션 "9월 A라인 목표 달성 검토"). */
export const SEED_CONVERSATION: ChatMessage[] = [
  {
    id: "seed-u1",
    role: "user",
    content:
      "9월 A라인에서 KRA-1180 1,000개가 목표인데 달성 가능한지 봐줘. 자재 제약도 같이 확인해줘.",
    parts: [],
    statuses: [],
    streaming: false,
    error: null,
  },
  {
    id: "seed-a1",
    role: "assistant",
    content: "",
    streaming: false,
    error: null,
    statuses: [
      { step: "analyze", label: "요청 분석", status: "completed" },
      { step: "query_database", label: "생산 실적 조회", status: "completed" },
      {
        step: "query_material",
        label: "자재 재고 · 소요 조회",
        status: "completed",
      },
      {
        step: "simulate_line_capacity",
        label: "라인 생산량 시뮬레이션",
        status: "completed",
      },
      {
        step: "simulate_material_constraint",
        label: "자재 제약 시뮬레이션",
        status: "completed",
      },
      { step: "compose", label: "결과 정리", status: "completed" },
    ],
    parts: [
      {
        kind: "tool" as const,
        id: "seed-tr1",
        result: {
        id: "seed-tr1",
        toolName: "query_database",
        content: null,
        data: {
          kind: "database",
          title: "A라인 KRA-1180 최근 4주 생산 실적",
          sql: "SELECT week, plan_qty, actual_qty,\n       ROUND(actual_qty / plan_qty * 100, 1) AS achieve_rate,\n       ROUND(run_minutes / avail_minutes * 100, 1) AS oee\nFROM mes.line_output\nWHERE line_code = 'A' AND item_code = 'KRA-1180'\n  AND week BETWEEN '2026-W32' AND '2026-W35'\nORDER BY week;",
          columns: ["주차", "계획", "실적", "달성률", "가동률"],
          rows: [
            ["2026-W32", "220", "214", "97.3%", "86.1%"],
            ["2026-W33", "240", "231", "96.3%", "87.4%"],
            ["2026-W34", "250", "238", "95.2%", "88.0%"],
            ["2026-W35", "250", "247", "98.8%", "89.6%"],
          ],
          note: "MES 기준 · 2026-09-07 23:00 마감",
        },
        },
      },
      {
        kind: "tool" as const,
        id: "seed-tr2",
        result: {
        id: "seed-tr2",
        toolName: "simulate_line_capacity",
        content: null,
        data: {
          kind: "simulation",
          scenario: "라인 생산량 시뮬레이션 · 9월 A라인",
          kpis: [
            { label: "최대 생산 가능", value: "1,120", unit: "개", tone: "ok" },
            { label: "목표 대비", value: "112", unit: "%", tone: "ok" },
            { label: "병목 공정", value: "본딩(Bonding)", tone: "warn" },
            { label: "소요 리드타임", value: "18", unit: "일" },
          ],
          summary:
            "라인 능력 기준 9월 목표 1,000개 대비 120개 여유. 본딩 공정 시간당 처리량(예상 72개/h)이 전체 처리량을 제약한다.",
          table: {
            columns: ["공정", "시간당 처리량", "일 가동시간", "월 캐파"],
            rows: [
              ["투입", "140개", "20h", "2,800개"],
              ["본딩", "72개", "20h", "1,440개"],
              ["검사", "96개", "20h", "1,920개"],
              ["포장", "160개", "20h", "3,200개"],
            ],
          },
        },
        },
      },
      {
        kind: "tool" as const,
        id: "seed-tr3",
        result: {
        id: "seed-tr3",
        toolName: "simulate_material_constraint",
        content: null,
        data: {
          kind: "simulation",
          scenario: "자재 제약 시뮬레이션 · KRA-1180",
          kpis: [
            { label: "제약 자재", value: "MDF-0563", tone: "block" },
            {
              label: "재고 기준 최대",
              value: "940",
              unit: "개",
              tone: "warn",
            },
            { label: "부족 수량", value: "60", unit: "개", tone: "block" },
            { label: "입고 예정", value: "09-16 · 240개", tone: "ok" },
          ],
          summary:
            "현재 재고 기준 최대 940개로 목표 대비 60개 부족. 9/16 예정된 MDF-0563 240개가 계획대로 입고되면 1,000개 충족 가능.",
          table: {
            columns: ["자재코드", "소요/개", "가용 재고", "생산 가능 수량"],
            rows: [
              ["MDF-0563", "1.0 EA", "940 EA", "940개"],
              ["ADH-2210", "0.4 EA", "620 EA", "1,550개"],
              ["FLM-1187", "1.0 EA", "1,180 EA", "1,180개"],
            ],
          },
        },
        },
      },
      {
        kind: "text" as const,
        id: "seed-txt-final",
        text:
          "## 결론\n\n" +
          "9월 A라인 KRA-1180 1,000개는 **자재 조건부 달성 가능**입니다.\n\n" +
          "- **라인 능력**: 최대 1,120개로 목표 대비 120개 여유. 병목은 본딩(Bonding) 공정입니다.\n" +
          "- **자재**: `MDF-0563` 재고 기준으로는 940개까지만 가능하며 60개가 부족합니다. 9/16 입고 예정 240개가 계획대로 들어오면 1,000개를 충족합니다.\n\n" +
          "| 구분 | 최대 생산 가능 |\n| --- | --- |\n| 라인 능력만 | 1,120개 |\n| 자재 제약 반영 | 940개 → 1,000개 (9/16 입고 시) |\n\n" +
          "### 다음 단계\n\n" +
          "MDF-0563 입고 일정을 구매팀과 확정하고, 입고 지연 시 본딩 공정 잔업으로 말일 3일간 일 40개 추가 생산이 가능한지 검토하십시오. (자재 기준일자 2026-09-07)",
      },
    ],
  },
];
