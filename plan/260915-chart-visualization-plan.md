# 차트 시각화 통합 계획

**상태: v2 Backend·Frontend 완료. 마지막 갱신: 2026-09-15.**

## 요구사항과 데이터 흐름

```text
Knowledge 확인 → 집계 SQL/시뮬레이션 → Result Store(result_id)
→ prepare_visualization → 서버 검증·등록(visualization_id)
→ 최종 답변 chart 마커 → GET /api/visualizations/{id} → bar/line 렌더링
```

- Agent가 질문과 실제 결과 컬럼을 바탕으로 `bar | line`, x, y와 선택적
  group을 제안하고 서버가 원본 결과로 검증한다.
- 집계·비율 계산은 SQL에서 끝내며 프론트가 재집계하거나 값을 보정하지 않는다.
- 최종 답변의 `chart` 코드 펜스에는 32자 hex `visualization_id` 하나만 넣는다.
- SQL·시뮬레이션 tool 카드에는 차트를 자동 첨부하지 않는다.
- 표시 한도는 포인트 500, 시리즈 8이며 초과 결과를 자르거나 자동
  다운샘플링하지 않는다.
- 시각화 메타데이터는 불변 JSON sidecar로 저장하고 원본 Result Store의
  만료 시각과 `access_scope`를 따른다.

## 공유 API

- `prepare_visualization` 성공 응답은 `visualization_id`와 필요한 경고만 반환한다.
- `GET /api/visualizations/{visualization_id}`는 검증된 `ChartSpec`과 표시
  메타데이터를 반환한다. URL query로 축이나 집계를 다시 지정하지 않는다.
- 잘못되거나 다른 scope의 ID는 404, 원본 만료·삭제는 410으로 처리한다.
- tool 오류 코드는 `RESULT_NOT_FOUND`, `RESULT_EXPIRED`, `RESULT_FORBIDDEN`,
  `RESULT_UNAVAILABLE`, `COLUMN_NOT_FOUND`, `INVALID_COLUMN_ROLE`,
  `DUPLICATE_MAPPING`, `DUPLICATE_GRAIN`, `EMPTY_RESULT`, `UNRENDERABLE_VALUES`,
  `DISPLAY_LIMIT_EXCEEDED`, `UNSUPPORTED_KIND`를 사용한다.
- `pp_session_scope`는 HttpOnly·SameSite=Lax 쿠키이며 로컬 HTTP에서는 Secure를
  끄고 운영 HTTPS에서는 켠다. 이는 사용자 인증이 아니라 결과 접근 범위다.

## 파트별 결과

- Backend: 결과·컬럼·grain·한도 검증, 시각화 저장소와 TTL 정리,
  `prepare_visualization`, 조회 API와 fake runner 연동을 완료했다.
- Frontend: 안전한 marker 파서, 중복 GET 결합과 취소·재시도, ChartSpec 런타임
  검증, Recharts bar/line 렌더링과 오류 fallback을 완료했다.

상세 실행·결정 기록은 [백엔드 계획](../backend/plan/260915-chart-v2-plan.md)과
[프론트 계획](../frontend/plan/260915-chart-v2-plan.md)에 보존한다.

## 인수 조건과 비범위

- 중복 grain, 잘못된 컬럼, 빈 결과, NULL, 시간 정렬과 표시 한도 오류를 조용히
  합산·잘라내지 않는다.
- streaming 중 미완성 marker와 완료 후 잘못된 marker가 무한 로딩으로 남지 않는다.
- tool 미호출이나 검증 실패 시 표·텍스트 응답이 유지된다.
- pie·간트와 자동 다운샘플링은 후속 별도 계획 전까지 지원하지 않는다.

## 후속: assistant-ui Tool UI 전환 (2026-09-16, 완료)

신규 응답의 표시 진입점을 최종 답변 `chart` marker에서
`prepare_visualization` standalone Tool UI로 전환했다. 검증·저장·조회 API와
ChartSpec은 유지하며 marker renderer는 과거 메시지 호환용으로 남긴다. 상세 범위와
검증은 [Tool UI 차트 계획](260916-assistant-ui-tool-ui-plan.md)을 따른다.
