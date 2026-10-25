import type { QueryTablePage } from "@/types/query-result";

export type LastPage = {
  resultId: string;
  requestBaseKey: string;
  value: QueryTablePage;
};

/**
 * 화면에 둘 페이지. 검색·정렬·페이지 크기를 바꿔 불러오는 동안에도 같은 결과의 마지막 표를 흐리게
 * 유지한다(비우면 검색창까지 다시 그려져 입력 중 포커스를 잃는다). 실패했을 때는 같은 조건의 결과만 유지한다.
 */
export function displayedTablePage(
  state: { type: string; value?: QueryTablePage; stale?: QueryTablePage },
  last: LastPage | null,
  resultId: string,
  requestBaseKey: string,
): QueryTablePage | null {
  if (state.type === "success") return state.value ?? null;
  if (state.type === "loading") return state.stale ?? (last?.resultId === resultId ? last.value : null);
  return last?.requestBaseKey === requestBaseKey ? last.value : null;
}
