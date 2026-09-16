# Agent Workbench UI/UX 감사 후속 개선 — Backend

**상태: 감사 완료 · 범위 내 구현·검증 완료 · 후속 계약 검토 보류. 마지막 갱신: 2026-09-16.**

- 상위 계획: [UI/UX 감사·공유 계약·인수 조건](../../plan/260916-agent-workbench-ux-audit-plan.md)
- Frontend 연계: [실행 계획](../../frontend/plan/260916-agent-workbench-ux-audit-plan.md)의
  FE-01·FE-04는 표/종료 상태 fixture를 공동 인수한다. 나머지 독립 개선을 막지 않는다.
- 착수 조건: [Backend 지침](../AGENTS.md)과 기존 이벤트·Tool 계약을 확인하고 mock/fake에서 재현한다.
- 범위: BE-01~03 계약 검증·회귀 fixture 완료. 이번 UX 구현에서 Backend 런타임/API는 변경하지 않았다.

## 1. 책임과 공통 원칙

Frontend UX 개선을 위해 불필요한 API를 추가하지 않는다. 공유 계약의 기본값은
**변경 없음**이며 AgentEvent·Tool payload·Result Store·시각화 계약은 상위 계획을 따른다.
이 실행 계획에서 새 필드·스키마·모델 설정값·가상 timing을 정의하지 않는다.

- 우선 수행: F01 표 문맥 계약, F02·F12 결과/종료 계약 검증과 mock/fake fixture.
- 후속 검토: F10 서버 실행 시간. Frontend의 실제 클라이언트 관측 시간 표시와 별개다.
- 보류: F17 실제 모델 설정 조회, F08 대화 영속 저장·분기 복원.
- 그 외 감사 항목은 Frontend가 담당하며 Backend API 추가의 근거가 되지 않는다.
- 기존 계약으로 재현·표시가 충분하면 런타임 코드는 변경하지 않는다. 부족한 경우
  상위 계획에서 변경 범위를 먼저 합의하고 양쪽 스키마·타입·파서를 함께 갱신한다.
- 완료된 표/스트리밍/지식 계획은 과거 이력으로 유지한다.

## 2. BE-01 — 표 문맥 계약 검증

- 감사 항목·우선순위: F01, P1.
- 검토 대상: `agent/agent.py`의 `_needs_table_fallback`, `_table_fallback_events`,
  `run_agent`와 기존 `prepare_table`/Result Store 경로.
  테스트 변경 대상: `tests/test_agent.py`, `tests/test_tools.py`의 관련 표 회귀.
- 요구 동작:
  - 표 요청 또는 Markdown 표 응답 뒤 모델이 호출을 빠뜨린 경우,
    마지막 접근 가능한 Result Store 결과를 사용하는 자동 `prepare_table` 조건을 확인한다.
  - 별도 지표의 Markdown 표와 자동 보완된 standalone 표가 함께 발생할 수 있음을 기록한다.
    “성공한 표가 존재한다”는 사실만으로 모든 텍스트 표가 같은 데이터라고 단정하지 않는다.
  - result_id·컬럼·행·지표 문맥 등 기존 정보로 확인할 수 있는 대응 범위를 검토한다.
    대응 관계를 확인하지 못한 표는 중복으로 확정하지 않는 원칙을 Frontend와 공유한다.
  - 기존 성공 `prepare_table` 후 불필요한 중복 보완 방지, 접근 범위·표시 한도·SQL 읽기 전용을 유지한다.
- 검증 방법:
  - 기존 성공 표 있음/없음, 표 요청 감지, Markdown 표 감지,
    별도 불량률 표와 WIP 결과, 접근 가능한 결과 없음을 mock으로 조합한다.
  - 자동 생성 이벤트와 모델 생성 이벤트의 result 참조·도착 순서·tool_call_id를 비교한다.
  - FE-01에서 각 사례의 Markdown 표와 standalone 표를 함께 렌더링해 보존 기대를 확인한다.
- 완료 조건:
  - [x] 자동 보완 발생 조건과 표 대응 관계의 확인 가능/불가능 범위를 기록한다.
  - [x] 무관한 표를 중복이라고 간주하지 않는 fixture와 기대 결과가 양쪽에서 일치한다.
  - [x] 기존 계약으로 충분한지 판정하고, 충분하면 런타임 무변경으로 완료한다.
  - [x] BE-03 및 7절의 필수 검증 결과를 새로 기록한다.

## 3. BE-02 — 실행 결과·종료 계약 검증

- 감사 항목·우선순위: F02(P1), F12(P2).
- 검토 대상: `agent/event_adapter.py`, `agent/agent.py`, `api/schemas.py`, 기존 chat SSE 경로.
  테스트 변경 대상: `tests/test_event_adapter.py`, `tests/test_agent.py`, `tests/test_api.py`.
- 요구 동작: Tool 실행 결과와 턴 종료를 구분하고 동일 호출의 연결을 검증한다.
  done은 턴 종료 신호이며 모든 Tool의 성공 증명이 아니다. 기존 이벤트에 없는 결과는 만들어내지 않는다.

| 시나리오 | 검증 내용 | Frontend 기대 |
| --- | --- | --- |
| Tool 오류 → 설명 text → 정상 턴 done | Tool 오류 정보 보존, 턴 종료와 별개 | 오류 이력 보이는 요약; 무조건 전체 성공/실패로 환원하지 않음 |
| tool_call → 결과 없이 done | 결과 누락이 숨겨지거나 성공 결과로 합성되지 않음 | 해당 호출 미완료 |
| 내용/Tool 결과 없이 done | 빈 출력 종료를 기존 계약으로 재현 | 빈 응답 안내 |
| SQL 성공 0행 → done | 0행 성공과 오류 payload를 구분 | 조회 결과 0건, 오류나 빈 assistant와 구별 |
| error → done | 기존 안전한 오류가 뒤따른 종료로 지워지지 않음 | 오류·복구 안내 유지 |
| 동시 호출과 순서가 바뀐 결과 | 같은 업무 호출의 tool_call/status/tool_result에 동일 tool_call_id | 다른 호출의 결과를 잘못 연결하지 않음 |
| Tool 오류 후 다른 Tool 성공 → text → done | 개별 결과·복구 맥락·최종 출력 보존 | 오류 이력과 유효한 최종 결과를 함께 표시 |

- 검증 방법: mock SDK/event 입력으로 adapter 출력부터 agent 종료, API SSE JSON까지
  계층별로 검사한다. 도구명만으로 연결하지 않고 실제 tool_call_id를 확인한다.
  불가능하거나 계약 위반인 조합은 지원 상태로 꾸미지 말고 이유·방어 표시 필요성을 기록한다.
- 완료 조건:
  - [x] 위 시나리오의 실제 이벤트 순서와 성공/오류/빈 값/누락 의미를 확인한다.
  - [x] 오류 후 done 및 호출 ID 매칭에 회귀 테스트가 있고 Frontend FE-01·FE-04와 기대가 일치한다.
  - [x] 공개 args에 내부 access scope/provider/예외가 노출되지 않으며 기존 turn/fork 계약을 유지한다.
  - [x] 계약 충족 여부와 BE-03·7절 검증 결과를 기록한다.

## 4. BE-03 — mock/fake 회귀 fixture와 공동 인수

- 감사 항목·우선순위: F01·F02(P1), F12(P2). BE-01~02를 지원하는 테스트 작업이다.
- 변경 대상: `tests/test_agent.py`, `tests/test_event_adapter.py`, `tests/test_api.py`,
  필요한 테스트 전용 fixture. 기존 `agent/fake_runner.py`는 재사용 가능성을 검토하며
  테스트만으로 재현 가능한 경우 운영/fake 기본 응답을 불필요하게 바꾸지 않는다.
- 요구 동작:
  - 외부 LLM/provider·사내 서비스 호출 없이 BE-01~02 상태를 결정적으로 재현한다.
  - 기존 공개 이벤트를 사용하며 새로운 테스트 전용 API나 production payload 필드를 만들지 않는다.
  - Frontend의 제어된 SSE 입력과 같은 사례 ID·이벤트 순서·표시 기대를 공유한다.
    fixture는 계약 검증용이며 실제 LLM의 모든 실행 패턴을 보장하지 않는다.
- 검증 방법: 대상 단위 테스트, API SSE 테스트와 전체 Backend 필수 테스트를 수행한다.
  이어 FE-01·FE-04 브라우저에서 별도 표·오류 요약·미완료·빈 응답·0행을 확인한다.
- 완료 조건:
  - [x] BE-01~02의 모든 지원 시나리오에 재현 가능한 fixture가 있다.
  - [x] 테스트가 결과 내용뿐 아니라 이벤트 순서·동일 tool_call_id·오류 후 done을 확인한다.
  - [x] Frontend가 같은 사례를 재현하고 표시 결과를 기록한다.
  - [x] 실제 명령/결과·남은 미검증 범위를 기록한다. 기존 계약이 충분하면 런타임은 그대로 둔다.

## 5. BE-04 — 서버 timing 후속 검토

- 감사 항목·우선순위: F10, 후속 검토(현재 구현 비범위).
- 검토 대상: 향후 `agent` 실행 경계·event adapter·API 계약. 이번에는 수정 대상 없음.
- 요구 동작: 정확한 서버 시간에는 측정 시작/종료 지점과 전송 의미의 별도 합의가 필요하다.
  큐 대기·도구 실행·전체 턴·전송 지연·취소/중단·병렬 호출의 범위를 먼저 구분한다.
  서버 시계와 클라이언트 시계를 섞어 단순 차감하거나 클라이언트 수신 간격을 서버 실행 시간으로 부르지 않는다.
- 검증 방법: 검토가 승인되면 실제 측정 경계와 중단/오류/동시 실행 시나리오를 정하고
  mock 가능한 clock 및 통합 측정으로 확인한다. 필드 이름·형식은 현재 확정하지 않는다.
- 완료 조건(향후 검토):
  - [ ] 도입 필요성·측정 의미·비용·지원 범위를 검토해 채택 또는 보류 근거를 기록한다.
  - [ ] 채택 시 상위 계획과 Backend 스키마·Frontend 타입/파서·테스트 변경 범위를 함께 승인한다.
  - [ ] FE-05의 클라이언트 관측 시간 구현을 본 검토 때문에 대기시키지 않는다.

## 6. BE-05 — 실제 모델 표시·대화 저장 검토 보류

- 감사 항목·우선순위: F17 실제 모델 설정, F08 영속 저장·분기 복원. 둘 다 보류.
- 검토 대상: 향후 설정 노출 정책·세션/이력 저장 계약. 이번에는 수정 대상 없음.
- 요구 동작:
  - 모델 표시 API를 만들기 전에 사용자에게 공개할 실제 설정 범위와 보안 경계를 합의한다.
    프론트의 고정 제어를 “준비 중/미연결”로 설명하는 개선은 독립적으로 수행한다.
  - 영속 대화 저장은 세션 식별·보존/삭제·접근 범위·이력 선택·분기 복원 계약이 필요한 별도 범위다.
    현재 데이터 교체 안내를 위해 저장 API나 복원 기능을 추가하지 않는다.
- 검증 방법: 추후 승인 시 설정 일치·비밀값 비노출 또는 저장/복구/분기/접근 격리
  시나리오를 별도 상위 계획에서 정의한다. 현 단계는 보류 경계와 Frontend 안내의 독립성을 확인한다.
- 완료 조건(향후 검토):
  - [ ] 실제 모델 설정 조회의 필요성·공개 범위를 별도 결정한다.
  - [ ] 영속 저장·분기 복원의 범위와 인수 조건을 별도 결정한다.
  - [ ] 이번 UX 계획의 전체 인수를 보류 기능 구현과 연결하지 않는다.

## 7. 구현 후 필수 검증

테스트/fixture를 포함해 Backend를 변경하는 Task에는 아래 명령을 적용한다.
구현 후 아래 명령을 실행했고 결과는 8절에 기록한다.

```bash
cd backend
python -m pytest -q
```

- [x] 대상 테스트와 전체 테스트의 명령·통과/실패/제외·남은 경고를 기록한다.
- [x] 기존 SQL 읽기 전용, mock/real 시그니처·반환 형태, scope·TTL·표시 한도,
  안전한 오류·공개 args·turn/fork 식별자에 회귀가 없음을 확인한다.
- [x] BE-01~03은 Frontend fixture 브라우저 인수 결과와 연결한다.
- [x] 실제 LLM/provider·폐쇄망 real 서비스 미검증은 fake 통과와 구분해 남긴다.
- [x] 계약 변경이 필요해졌다면 먼저 상위 계획을 갱신하고 양쪽 타입·파서와 필수 검증을 함께 처리한다.
- [x] 상위 계획·양쪽 실행 계획·Todo의 상태를 일치시킨다.

## 8. 결정·실행 기록

- 2026-09-16: Backend 책임을 계약 검증·회귀 fixture로 제한했다. 새 API·payload
  필드는 확정하지 않았고 기존 계약이 충분하면 런타임 무변경을 원칙으로 한다.
- 서버 timing은 후속 검토, 실제 모델 설정·영속 대화/분기 복원은 보류다.
  Frontend 안내·관측 시간 구현의 선행 조건으로 삼지 않는다.
- 감사 시점의 채팅 11개·지식 관리 5개 브라우저 통과는
  [상위 기록](../../plan/260916-agent-workbench-ux-audit-plan.md)에 보존한다.
  이는 이번 Backend fixture 작성·검증 완료의 증거가 아니다.
### 구현·계약 판단

- [test_workbench_contract.py](../tests/test_workbench_contract.py)에 **9개** 결정적 테스트를 추가했다.
  SDK query를 monkeypatch하고 실제 event_adapter → run_agent → API SSE 경로를 검증한다.
  외부 provider나 운영 DB를 호출하지 않으며 공개 이벤트만 사용한다.
- BE-01: 별도 불량률 Markdown 표 뒤 마지막 WIP Result Store 결과를 자동 prepare_table로
  보완하는 경우와 접근 가능한 result_id가 없는 경우를 검증했다.
  자동 보완은 텍스트 표의 의미적 동일성을 보장하지 않는다. 기존 성공 표의 중복 보완 방지와
  fallback 조건은 기존 회귀로 유지한다. Frontend는 검증된 컬럼/행 대응만 사용하고 모호하면 보존한다.
- BE-02: 7개 사례 ID를 Frontend 단위 fixture와 맞췄다.
  tool-error-done, missing-result, empty-done, zero-rows, error-done,
  parallel-reversed, recovered-tool-error에 대해 이벤트 순서·tool_call_id·오류·종료를 확인했다.
  done은 성공 합성 신호가 아니며 누락 결과를 만들지 않는다. 오류 후 설명/성공 결과도 보존된다.
- BE-03: 테스트 전용 입력으로 재현 가능해 fake_runner 기본 응답이나 런타임은 변경하지 않았다.
  호출 ID, turn anchor, 공개 args의 안전성을 확인했다. 신규 payload/API는 필요하지 않다.
- Frontend는 같은 7개 종료 사례와 표 보존을 단위 테스트로 검사하고,
  실제 App 브라우저에서 오류+누락, 빈 응답, 0행, 별도 표의 표시를 검증했다.
  모든 7개 사례를 각각 별도 브라우저 E2E로 실행했다는 의미는 아니다.

### 구현 후 실행 결과

- `python -m pytest -q tests/test_workbench_contract.py`: **9개 통과**.
- `python -m pytest -q`: **259개 통과, 6개 deselected**.
- Frontend 새 회귀 결과는 [Frontend 9절](../../frontend/plan/260916-agent-workbench-ux-audit-plan.md)에 연결했다.
- 기존 SQL 읽기 전용·Result Store scope/TTL·표시 한도·안전한 오류·fork 테스트도 전체 suite로 회귀했다.
- 실제 SDK/provider·폐쇄망 real 서비스는 미검증이며 mock 통과로 대체하지 않는다.
- BE-04~05는 미구현/보류 유지. 서버 timing·모델 설정 API·영속 저장을 이번 UX 완료 조건에 포함하지 않는다.
