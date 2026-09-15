# 전체 시스템 리팩토링 backend 실행 계획

**상태: 완료. 마지막 갱신: 2026-09-15.**

- 상위: [전체 시스템 계획](../../plan/260915-full-stack-refactoring-plan.md)
- 상대 파트: [실행 계획](../../frontend/plan/260915-full-stack-refactoring-plan.md)
- 착수 조건: 기존 지침·활성 계약·기준선 분석 완료. 공유 payload는 상위 계약을 따른다.

## Tasks

### B1. SDK 오류·완료 lifecycle

- 대상: agent/event_adapter.py, agent/agent.py, tests/test_event_adapter.py, tests/test_agent.py.
- 이유/동작: SDK 실패 원문 숨김, 업무 오류 status 일치, 성공한 SDK 종료만 turn anchor 기록.
- 선행: 상위 F03~F05. 위험: 알 수 없는 fork 경고를 최종 SDK 실패와 혼동하지 않음.
- 검증/완료: adapter/agent tests로 정상·실패·조기 종료·cancel/fork 회귀 통과.

### B2. 저장 결과 접근과 SQL 경계

- 대상: tools/result_tool.py, services/mock/mock_sql_service.py, tests/test_tools.py, tests/test_services.py.
- 이유/동작: TTL/scope/손상 결과 확인, SQLite 실제 read 테이블 검사. Result Store wire payload와 mock/real signature 유지.
- 선행: B1 통과. 위험: CTE·정상 인용 식별자 거부, 기존 unscoped 결과 호환.
- 검증/완료: 만료·삭제·손상·scope 및 quoted table 우회 실패, 정상 SQL/inline/large_result 통과.

### B3. 작은 경계·문서 보정 및 전체 검증

- 대상: core/config.py, agent/agent.py, tools/sql_tool.py, 관련 테스트/실행 계획.
- 이유/동작: 환경변수 읽기 위치와 실제 100행 기준 일치.
- 선행: B2. 위험: monkeypatch 기반 fake 테스트 동작 보존.
- 검증/완료: 전체 pytest와 mock/real signature parity. Backend 별도 lint/type-check는 설정되어 있지 않음.

## 결정·실행 기록

- 2026-09-15: 소스 수정 전 계획 작성. 새 의존성·protocol 교체 없이 실패 재현과 점진 수정 진행.

### 완료 Task와 회귀

- [x] B1: SDK raw 도구 실패를 안전한 status:error payload로 변환; 업무 status:error도 진행 실패 표시. ResultMessage 성공 여부를 추적하고 정상 query 종료 후 session/anchor 반영.
- [x] B2: Result 조회 전 scope/TTL 검사, 손상/삭제 오류 정규화. SQL 실행 연결에 SQLite authorizer 추가. 정규식 검사를 통과한 quoted/commented 미등록 테이블도 거부하며 정상 CTE 허용.
- [x] B3: fake flag는 core/config.py에서 호출 시 읽고 기존 monkeypatch 동작 유지. SQL tool 설명을 실제 100행 기준으로 보정.

추가 테스트: test_agent 4개(error/eof/cancel 및 old cancel→new session),
test_event_adapter 2개(업무 실패·SDK 원문 비노출), test_api 1개(client disconnect),
test_services 6개(인용/주석 우회 4, 정상 CTE 1, signature parity 1),
test_tools 10개(summary/page 각각 만료·삭제·손상 metadata·손상 parquet·다른 scope).

검증 기록:

- 기준선 전체: 194 passed, 5 deselected.
- B1 실패 재현 5개 → 수정 후 agent/adapter/API 36 passed.
- B2 실제 문제 12개 재현. signature 테스트 표현 차이 1개는 테스트를 보정. CTE COUNT database=None 콜백을 허용한 뒤 tools/services/guard/store 80 passed.
- 최종 `python -m pytest -q`: **217 passed, 5 deselected in 5.86s**.
- 실 provider E2E 5개는 인증을 사용하지 않아 미실행. 실제 real 서비스 성공 응답은 stub으로 미검증. signature parity와 기존 validation은 검증.
- 별도 Backend lint/type-check는 설정되어 있지 않아 실행하지 않음.

성공한 fork와 unknown/empty fallback, ResultMessage.uuid 제외 테스트는 계속 통과한다.
오류·취소 cleanup에서 session을 변경하지 않는 내부 구현 변경이며 공개 schema는
바꾸지 않았다. Result tool의 legacy unscoped 데이터 호환도 유지했다.

변경 파일:

- agent/agent.py, agent/event_adapter.py
- core/config.py
- services/mock/mock_sql_service.py
- tools/result_tool.py, tools/sql_tool.py
- tests/test_agent.py, tests/test_api.py, tests/test_event_adapter.py, tests/test_services.py, tests/test_tools.py
- 본 실행 계획 (공통 결과/계약/Todo는 상위 계획에서 관리)
