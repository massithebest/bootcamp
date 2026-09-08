/**
 * Frontend 전용(UI) 타입.  Backend Contract 와 무관하며,
 * 현재 단계에서는 하드코딩된 더미 데이터로 채운다.
 * 향후 Backend Memory / History / Skills API 와 연결할 때의 인터페이스 형태를 잡아 둔다.
 */

/** 세션에서 주로 쓰인 도구 흔적. 사이드바 세션 항목에 표식으로 노출한다. */
export type ToolTrace = "query" | "document" | "simulation";

export interface Session {
  id: string;
  title: string;
  /** 마지막 활동 시각 (표시용 문자열). */
  lastActivity: string;
  /** 시간 그룹핑 키. */
  group: "today" | "week" | "earlier";
  /** 이 세션에서 실제 실행된 도구 종류. */
  traces: ToolTrace[];
}

/** 에이전트가 보유한 능력. */
export interface Skill {
  /** Backend tool_name 과 매핑되는 식별자. */
  toolName: string;
  label: string;
  description: string;
  enabled: boolean;
  lastCalledAt: string | null;
}

/** 현재 세션의 실행 정보. */
export interface SessionMetadata {
  model: string;
  toolCallCount: number;
  lastResponseSeconds: number | null;
  avgResponseSeconds: number | null;
  /** 참조한 데이터 기준일자. */
  dataAsOf: string;
  /** 시뮬레이션 서버 상태. */
  simulationServer: {
    status: "ok" | "warn" | "block";
    label: string;
  };
}

export interface PromptRevision {
  version: string;
  editedAt: string;
  editedBy: string;
  note: string;
}

export interface SystemPromptState {
  content: string;
  revisions: PromptRevision[];
}

export interface CurrentUser {
  name: string;
  team: string;
}
