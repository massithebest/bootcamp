/**
 * 읽기 전용 지식 조회 API (`/api/knowledge/*`).
 *
 * Backend 통신은 `chat-api.ts` 와 같은 base URL 설정을 쓴다. 채팅과 달리
 * 스트리밍이 아니라 단순 GET 이므로 여기 별도로 둔다.
 */

import { API_BASE_URL } from "./chat-api";
import type { Skill } from "@/types/workspace";

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw new Error(`${path} 요청 실패 (${response.status})`);
  }
  return (await response.json()) as T;
}

/** 에이전트가 선택할 수 있는 Skill 목록. */
export function fetchKnowledgeSkills(signal?: AbortSignal): Promise<Skill[]> {
  return getJson<Skill[]>("/api/knowledge/skills", signal);
}
