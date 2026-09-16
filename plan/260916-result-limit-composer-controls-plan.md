# 조회 한도·표시 한도와 Composer 표시 제어 계획

**상태: 완료 · 2026-09-16**

## 목표와 계약

- `execute_sql`은 한 요청에서 원본 데이터를 최대 1,000행까지 조회·저장한다.
  1,001번째 행은 `source_truncated` 판정에만 사용한다.
- Frontend의 모든 데이터 표는 원본 payload 크기와 관계없이 데이터 행을 최대
  10개만 렌더링한다. 공용 `DataTable`과 assistant 응답 Markdown 표에 같은
  제한을 적용한다.
- 대량 결과의 `row_count`, Result Store, 요약과 시각화용 원본은 최대 1,000행을
  유지한다. 10행 제한은 화면 표시 정책이며 데이터 계약을 축소하지 않는다.
- Composer 왼쪽 아래에 첨부, 현재 모델 `GLM-5.3-Flash`, 추론 강도 `Low`를
  표시한다. 이번 단계에서는 전송 계약과 Backend 옵션에 연결하지 않고 준비 중인
  제어임을 접근 가능한 설명과 비활성 상태로 명시한다.
- `AgentEvent`와 tool payload 스키마는 변경하지 않는다.

## 파트별 작업

- Backend: SQL guard 상한과 관련 문서·테스트를 1,000행으로 갱신하고 Agent가
  최종 Markdown 표를 10행 이내로 작성하도록 지침을 추가한다.
- Frontend: 공용 표 렌더러 두 경로를 10행으로 제한하고 생략 안내를 표시한다.
  Composer 준비 중 제어 3종을 추가한다.

## 완료 조건

- 1,000행 조회·저장 및 1,001행 초과 판정이 테스트로 확인된다.
- tool result와 Markdown 표가 데이터 행을 각각 최대 10개만 렌더링한다.
- 첨부·모델·추론 강도 UI가 빈 Thread와 진행 중 Thread 양쪽 Composer에 보인다.
- Backend 전체 테스트와 Frontend test/build/lint, 브라우저 화면 검증이 통과한다.

## 완료 기록

- SQL 결과는 최대 1,000행을 저장하고 초과 여부 판정용 1행만 추가 조회한다.
- 공용 DataTable과 Markdown 표 모두 데이터 행 10개 및 생략 건수를 표시한다.
- Composer 준비 중 제어 3종을 추가하고 데스크톱·400px 화면을 검증했다.
- Backend 전체 테스트와 Frontend test/build/lint를 통과했다.
