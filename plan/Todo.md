# Production Planning Agent 요구사항 및 Todo

**상태: 진행 중. 마지막 갱신: 2026-09-16.**

이 문서는 프로젝트 요구사항, 완료 현황, 수행할 일과 결정 대기 항목을 함께
관리하는 단일 기준 문서다. 기능별 상세 설계와 완료 조건은 같은 폴더의 날짜형
상위 계획에서, 파트별 실행 이력은 `backend/plan`과 `frontend/plan`에서 관리한다.

## 목표

생산계획 담당자와 현장 관리자가 SQL이나 사내 시뮬레이션 도구를 직접 다루지
않아도 자연어로 데이터를 조회하고, 원인을 분석하며, 결과를 표와 차트로
확인할 수 있는 폐쇄망용 에이전트를 제공한다.

## 주요 사용 흐름

1. 사용자가 생산계획·실적·원인에 관한 질문을 입력한다.
2. Agent가 필요한 도메인 지식과 테이블·KPI·recipe를 조회한다.
3. 읽기 전용 SQL 또는 시뮬레이션을 실행하고 결과를 저장한다.
4. 근거 수치와 필요 시 검증된 차트를 포함해 답한다.
5. 사용자는 후속 질문, 편집, 재생성으로 분석을 이어간다.

## 범위와 비범위

지원 범위는 자연어 SQL 조회, 생산계획 시뮬레이션, 도메인 지식 조회,
대용량 결과 참조, bar/line 차트, 대화 분기와 폐쇄망 배포다.

현재 비범위는 운영 데이터 쓰기, pie·간트 차트, 모바일 최적화와 조직 단위
권한 관리다. SQL은 항상 조회 전용으로 제한한다.

## 요구사항 및 수행 현황

| 순번 | 기능 | 우선순위 | Backend | Frontend | 상태 및 기준 문서 | 수행일자 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 기본 채팅·SQL·SSE `AgentEvent` | - | 완료 | 완료 | 완료 | 2026-09-08 |
| 3 | 3-pane 워크벤치와 편집·재생성·취소·복사 | - | 완료 | 완료 | 완료 | 2026-09-14 |
| 2 | 도메인 지식 Phase 1과 현재 조회 UI | - | 완료 | 완료 | [도메인 지식 계획](260914-domain-knowledge-plan.md) | 2026-09-14 |
| - | 도메인 지식 작성·관리 UI와 Phase 2 입력·집계 진단 | - | 완료 | 완료 | [지식 관리 계획](260916-knowledge-management-plan.md) | 2026-09-16 |
| - | 도메인 지식 Phase 3 Milvus·문서 색인 | P3 | 미착수 | 후속 | [도메인 지식 계획](260914-domain-knowledge-plan.md) | - |
| 4 | Result Store 1차 | - | 완료 | 완료 | [Result Store 계획](260915-result-store-plan.md) | 2026-09-15 |
| 5 | 차트 시각화 v2 | - | 완료 | 완료 | [차트 계획](260915-chart-visualization-plan.md) | 2026-09-15 |
| 7 | assistant-ui 감사 후속 개선 | - | 해당 없음 | 완료 | [프론트 실행 계획](../frontend/plan/260915-assistant-ui-audit-plan.md) | 2026-09-15 |
| 8 | SMT2020 SQLite 및 Mock 전환 | - | 완료 | 완료 | [SMT2020 Mock 데이터 계획](260915-smt2020-mock-data-plan.md) | 2026-09-15 |
| - | Mock에서 실제 사내 서비스로 전환 | P3 | 진행 중 | 해당 없음 | [백엔드 폐쇄망 가이드](../backend/docs/CLOSED_NETWORK_SETUP.md) | - |
| 6 | 문서 역할 분리와 Agent 공통 지침 | - | 완료 | 완료 | 완료 | 2026-09-15 |
| 9 | frontend-design Skill 기반 3-pane 워크벤치 UI/UX 개선 | - | 해당 없음 | 완료 | [Frontend UI/UX 계획](260916-frontend-ui-ux-plan.md) | 2026-09-16 |
| 10 | assistant-ui Elements 기반 공통 프론트엔드 전환 | - | 해당 없음 | 완료 | [Elements 전환 계획](260916-assistant-ui-elements-plan.md) | 2026-09-16 |
| 11 | assistant-ui 홈페이지형 Composer와 공개 실행·답변 스트리밍 | - | 완료 | 완료 | [스트리밍 UI 계획](260916-assistant-ui-streaming-plan.md) | 2026-09-16 |
| 12 | 조회 1,000행·Composer 준비 중 제어(당시 표시 10행 정책은 #15에서 대체) | - | 완료 | 완료 | [조회·Composer 계획](260916-result-limit-composer-controls-plan.md) | 2026-09-16 |
| 13 | 중첩 Tool Reasoning과 호출 상세 | - | 완료 | 완료 | [중첩 Tool Reasoning 계획](260916-nested-tool-reasoning-plan.md) | 2026-09-16 |
| 14 | assistant-ui Tool UI 기반 차트 표시 | - | 완료 | 완료 | [Tool UI 차트 계획](260916-assistant-ui-tool-ui-plan.md) | 2026-09-16 |
| 15 | assistant-ui Tool UI 기반 대화형 표·표시 100행 | - | 완료 | 완료 | [대화형 표 계획](260916-interactive-table-tool-ui-plan.md) | 2026-09-16 |
| 16 | TanStack Table 전환과 표·차트 문맥 순서 | - | 완료 | 완료 | [TanStack Table·메시지 순서 계획](260916-tanstack-table-message-order-plan.md) | 2026-09-16 |
| 17 | 카탈로그 Tool 선택 인자 스키마 수정 | - | 완료 | 해당 없음 | [카탈로그 Tool 스키마 계획](260916-optional-catalog-tool-schema-plan.md) | 2026-09-16 |
| 18 | ChatGPT형 좌측 전역 내비게이션 | - | 해당 없음 | 완료 | [사이드바 내비게이션 계획](260916-sidebar-navigation-plan.md) | 2026-09-16 |
| 19 | 좌측 채팅 메뉴 단일화 | - | 해당 없음 | 완료 | [채팅 메뉴 단일화 계획](260916-chat-navigation-unification-plan.md) | 2026-09-16 |
| 20 | 공개 실행 안내 가독성·지속성 | - | 해당 없음 | 완료 | [실행 안내 가독성 계획](260916-reasoning-readability-plan.md) | 2026-09-16 |
| 21 | 지식 관리 구조화 상세 가독성 | - | 해당 없음 | 완료 | [지식 상세 가독성 계획](260916-knowledge-detail-readability-plan.md) | 2026-09-16 |
| 22 | 지식 Query 규칙·시각화 안내 계약 | - | 완료 | 완료 | [지식 Query 규칙 계획](260916-knowledge-query-rules-plan.md) | 2026-09-16 |
| - | Agent Workbench UI/UX 감사 후속 개선 | - | 계약 검증 완료 | 완료 | F01~F17 범위 내 구현·검증 완료, 후속 계약 검토 보류 — [상위·파트별 계획](260916-agent-workbench-ux-audit-plan.md) | - |
| - | 후속질문 동적 생성 | P1 | 미착수 | 미착수 | [후속질문 계획](260916-followup-suggestions-plan.md) | - |

P1~P3는 미수행 항목 간 상대적 우선순위이며 숫자가 낮을수록 먼저 착수한다.
근거는 아래 "다음 우선순위"에 정리한다. 순번·수행일자는 git 커밋 이력 기준 실제
완료 순서이며, 표의 행 순서(기능 그룹핑)와는 다를 수 있다. 미수행 항목은
순번·수행일자를 `-`로 표기한다.

## 공통 계약 및 비기능 요구사항

- 외부 CDN·폰트·브라우저의 LLM provider 직접 호출 없이 폐쇄망에서 동작한다.
- 신규 패키지는 사내 저장소에서 정확한 버전과 전이 의존성을 확보할 수 있어야 한다.
- 비밀값과 사내 주소는 환경 설정으로만 주입하고 버전관리에 포함하지 않는다.
- `AgentEvent`와 tool 결과 계약을 변경할 때 백엔드 스키마와 프론트엔드
  타입·파서를 같은 작업에서 갱신한다.
- Result Store, `prepare_table`, `prepare_visualization`, `/api/visualizations/{id}`와
  `pp_session_scope`의 계약 및 접근 범위·TTL을 유지한다.
- 도메인 지식 YAML과 Agent tool의 경계를 유지하고 내부 파일 경로를 API
  payload에 포함하지 않는다.
- 오류 응답에는 내부 예외, 비밀값과 서버 파일 경로를 노출하지 않는다.

## 수행해야 할 일

- [x] [Agent Workbench UI/UX 감사 후속 개선](260916-agent-workbench-ux-audit-plan.md) — F01~F17 프론트 구현·백엔드 계약 회귀 완료. 서버 timing·실제 모델 설정·대화 영속 저장은 보류
- [x] 화면 전환 확인창 제거 — 새 채팅·예시 세션은 즉시 전환, 지식 편집 보호·재생성 확인 유지. 테스트·빌드·브라우저 검증 완료 ([후속 단계](260916-agent-workbench-ux-audit-plan.md#9-후속-정책-화면-전환-확인창-제거))
- [x] 우측 Context Inspector 너비 조절 — 포인터 드래그·키보드 조절, 반응형 상한과 Chat 최소 폭 보호 ([후속 단계](260916-agent-workbench-ux-audit-plan.md#10-후속-기능-context-inspector-너비-조절))
- [ ] [후속질문 동적 생성](260916-followup-suggestions-plan.md) — 응답 내용 기반 2~4개 제안, 도메인 지식 힌트 참고, `done` 이벤트 확장
- [x] [누적 미커밋 변경 통합 검토](260916-uncommitted-review-plan.md) — 결과 문맥 보존·오탐·종료 상태·접근성 수정 및 필수/브라우저 검증

- [x] [assistant-ui Elements 기반 프론트엔드 전환](260916-assistant-ui-elements-plan.md) — 공식 shadcn 설치 및 Elements 카탈로그 5종 추가 적용 완료
- [x] [assistant-ui 홈페이지형 Composer와 공개 실행·답변 스트리밍](260916-assistant-ui-streaming-plan.md)
- [x] [조회 1,000행·Composer 준비 중 제어](260916-result-limit-composer-controls-plan.md) — 당시 표시 10행 정책은 대화형 표 계획에서 100행으로 대체
- [x] [중첩 Tool Reasoning과 호출 상세](260916-nested-tool-reasoning-plan.md)
- [x] [assistant-ui Tool UI 기반 차트 표시](260916-assistant-ui-tool-ui-plan.md)
- [x] [assistant-ui Tool UI 기반 대화형 표·표시 100행](260916-interactive-table-tool-ui-plan.md)
- [x] [TanStack Table 전환과 표·차트 문맥 순서](260916-tanstack-table-message-order-plan.md)
- [x] [카탈로그 Tool 선택 인자 스키마 수정](260916-optional-catalog-tool-schema-plan.md)
- [x] [ChatGPT형 좌측 전역 내비게이션](260916-sidebar-navigation-plan.md) — 좌측 메뉴로 채팅·지식 관리 전환, 대화 상태 보존
- [x] [좌측 채팅 메뉴 단일화](260916-chat-navigation-unification-plan.md) — `새 채팅`만 유지, 최근 대화로 복귀
- [x] [공개 실행 안내 가독성·지속성](260916-reasoning-readability-plan.md) — 요청 분석 가독성 강화, 실행 Tool 직전 안내·지속 회전 표시
- [x] [지식 관리 구조화 상세 가독성](260916-knowledge-detail-readability-plan.md) — raw JSON을 필드·태그·컬럼·목록 UI로 정리
- [x] [전체 시스템 근거 기반 감사 및 리팩토링](260915-full-stack-refactoring-plan.md) — 선정 P0/P1 및 소규모 P2 구현·검증 완료
- [x] SMT2020 HVLM/LVHM 원본을 단일 SQLite DB로 변환
- [x] 기존 합성 FGS/MP 시드와 mock을 SMT2020 SQL·입력 검증 mock으로 교체
- [x] SMT2020 기반 Fake Runner와 프론트 예시·관통 흐름 검증
- [x] 도메인 지식 Phase 2: SMT2020 입력 관계·dataset 혼합·조인 중복 집계 diagnostics 보강
- [x] table·recipe 조회 규칙과 table 시각화 안내 추가, sample query의 데이터 종속 답변 제거
- [ ] 실제 생산 부진 원인 시나리오와 현업 지식 검증 — 업무 데이터 확보 후
- [x] 텍스트 지식 등록·검토·버전·활성화·공용 관리 모드 구현
- [x] 지식 조회·관리 화면, 도구/Skills 설명, local 검색과 정확한 버전 인용 구현
- [x] 별도 관리 활성화 환경변수 없이 기존 구조화 YAML을 항상 읽기 전용으로 표시
- [x] table·recipe 샘플 SQL을 데이터 비종속 질문·SQL 형식으로 통일
- [x] 우측 패널을 도구·스킬·지식 순서와 설명이 보이는 간결한 지식 목록으로 개편
- [ ] 도메인 지식 Phase 3: 폐쇄망용 비정형 문서 색인과 real RAG 연결
- [x] assistant-ui 감사 계획의 6개 후속 개선 항목 구현
- [ ] 실제 사내 DB·RAG·시뮬레이션 서비스를 `services/real`에 연결
- [ ] Result Store의 후속 필터·재집계 기능과 저장 백엔드 전환 검토
- [x] Claude 프론트엔드 스킬(frontend-design)을 활용한 3-pane 워크벤치 UI/UX 개선
- [ ] Codex(GPT-5.1 Astra 모델)를 활용한 백엔드·프론트엔드 전반 코드 리팩토링 및 개선

## 다음 우선순위

1. 후속질문 동적 생성 (P1)
2. 확장한 diagnostics와 실제 업무 정의의 현업 검토 (P2)
3. 실제 생산 부진 원인 시나리오 보강 — 업무 데이터 확보 후 (P2)
4. 폐쇄망 실제 DB·Milvus/RAG·시뮬레이션 연결 (P3)

UI/UX 감사 F01~F17의 프론트 개선과 백엔드 계약 검증은 2026-09-16 완료했다.
새 브라우저 회귀와 필수 테스트 결과는 [상세 계획](260916-agent-workbench-ux-audit-plan.md) 8절에 기록했다.
서버 timing·실제 모델 설정·대화 영속 저장은 계속 보류하며 실제 스크린리더·운영 환경 검증은 남아 있다.

~~assistant-ui 감사 후속 개선~~은 2026-09-15 완료. 근거는 [프론트 실행 계획](../frontend/plan/260915-assistant-ui-audit-plan.md) 12절 실행 기록.

~~SMT2020 SQLite 및 Mock 전환~~은 2026-09-15 완료. 합성 FGS/MP 데이터는
[SMT2020 Mock 데이터 계획](260915-smt2020-mock-data-plan.md)의 실제 benchmark
DB와 입력 정합성 mock으로 대체했다.

## 보류·결정 필요

- 텍스트 지식 활성화는 모든 대화의 이후 검색 대상을 제어한다. 도구 권한과 구조화 YAML은 변경하지 않는다.
- 실제 테이블명·컬럼·KPI 공식·단위는 현업 검증 후 `draft`에서 `verified`로
  변경해야 한다.
- 다중 사용자 인증과 권한 연결 전까지 `pp_session_scope`는 동일 브라우저의
  결과를 구분하는 범위 토큰으로만 사용한다.
- pie·간트 차트와 모바일 UI는 현재 범위 밖이다.

## 프로젝트 완료 조건

- 계획된 조회·분석·시뮬레이션 흐름이 실제 사내 서비스와 연결된다.
- 프론트엔드와 백엔드의 공유 API·타입 계약이 일치한다.
- 폐쇄망 설치·실행·복구 절차가 검증된다.
- 관련 기능 계획, 파트별 실행 계획과 이 문서의 상태가 일치한다.

## 기능별 기준 계획

- [Agent Workbench UI/UX 감사 후속 개선](260916-agent-workbench-ux-audit-plan.md)
- [후속질문 동적 생성](260916-followup-suggestions-plan.md)
- [도메인 지식](260914-domain-knowledge-plan.md)
- [지식 관리 UI·local 검색](260916-knowledge-management-plan.md)
- [Result Store](260915-result-store-plan.md)
- [차트 시각화](260915-chart-visualization-plan.md)
- [SMT2020 SQLite 및 Mock 전환](260915-smt2020-mock-data-plan.md)
- [전체 시스템 리팩토링](260915-full-stack-refactoring-plan.md)
- [Frontend UI/UX 개선(frontend-design)](260916-frontend-ui-ux-plan.md)
- [ChatGPT형 좌측 전역 내비게이션](260916-sidebar-navigation-plan.md)
- [좌측 채팅 메뉴 단일화](260916-chat-navigation-unification-plan.md)
- [공개 실행 안내 가독성·지속성](260916-reasoning-readability-plan.md)
- [지식 관리 구조화 상세 가독성](260916-knowledge-detail-readability-plan.md)

- [assistant-ui Elements 전환](260916-assistant-ui-elements-plan.md)
