# Result Store 통합 계획

**상태: 1차 Backend·Frontend 완료, 후속 연산 미착수. 마지막 갱신: 2026-09-15.**

## 요구사항과 계약

- SQL과 표형 시뮬레이션 결과는 크기와 관계없이 저장하고 uuid4 hex
  `result_id`를 발급한다.
- 100행 이하는 `type: inline`으로 전체 행을, 초과 결과는
  `type: large_result`로 컬럼·앞 10행·요약 통계만 Agent에 전달한다.
- 저장 형식은 parquet, 메타데이터는 JSON sidecar이며 내부 경로는 tool payload에
  노출하지 않는다.
- `get_result_summary`와 `get_result_page`는 Agent가 필요한 범위만 다시 읽는
  경로다. 프론트는 Result Store에 직접 접근하지 않는다.
- 기본 TTL은 24시간이며 만료 결과와 메타데이터를 주기적으로 정리한다.
- `access_scope`가 다른 결과는 존재 여부를 노출하지 않는다.

## 파트별 결과

- Backend: 공통 `ResultStore` 인터페이스, 로컬 parquet 구현, SQL·시뮬레이션
  저장, 요약·페이지 tool과 TTL 정리를 완료했다.
- Frontend: `large_result`를 전체 표 대신 행 수, 샘플과 통계가 포함된 요약 카드로
  렌더링한다. 직접 페이지네이션은 제공하지 않는다.

상세 실행·결정 기록은 [백엔드 계획](../backend/plan/260915-result-store-plan.md)과
[프론트 계획](../frontend/plan/260915-result-store-plan.md)에 보존한다.

## 후속 범위

- `filter_result`, `aggregate_result`는 새 `result_id`를 발급하는 방식으로 설계한다.
- 저장 백엔드를 RDB로 교체해도 tool과 호출부가 바뀌지 않도록 인터페이스 경계를
  유지한다.
- 실제 질의 로그를 기준으로 inline 임계값과 샘플 크기를 재평가한다.

## 인수 조건

- 소량·대용량 결과 모두 `result_id`, 컬럼 메타데이터와 정확한 `row_count`를 가진다.
- 대용량 원본은 Agent 컨텍스트에 포함되지 않지만 summary/page tool로 조회할 수 있다.
- 만료·손상·접근 범위 오류가 내부 파일 정보를 노출하지 않고 처리된다.
- 차트는 동일 `result_id`를 사용하되 [차트 계획](260915-chart-visualization-plan.md)의
  검증·조회 경계를 따른다.
