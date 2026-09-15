# 도메인 지식 통합 계획

**상태: Phase 1 및 현재 프론트 연동 완료, Phase 2·3 미착수. 마지막 갱신: 2026-09-15.**

## 요구사항

- 구조화 가능한 테이블·조인·KPI·시뮬레이션·recipe는 YAML을 단일 기준으로
  관리한다.
- 분석 절차는 Skill, 비정형 매뉴얼·정책·보고서는 RAG로 관리하며 같은 사실을
  여러 채널에 복제하지 않는다.
- Agent는 파일을 직접 읽지 않고 `list_*`, `describe_*`, `get_*`,
  `search_knowledge` tool을 통해 지식을 조회한다.
- 모든 지식은 `draft | verified`, owner, source, updated 메타데이터로 검증 상태를
  구분한다.
- 프론트는 읽기 전용 지식 API와 `tool_result.data.kind`를 통해 참조한 지식을
  표시한다.

테이블 grain, KPI 공식, recipe/CTE 작성과 검증 방법은
[백엔드 도메인 지식 관리 지침](../backend/docs/domain-knowledge-management.md)을
따른다.

## 단계와 파트별 할당

| 단계 | Backend | Frontend | 상태 |
| --- | --- | --- | --- |
| Phase 1 | YAML 로더, 카탈로그·KPI·recipe tool, 읽기 전용 SQL, 시드 DB, 시나리오, 지식 API | catalog 결과 카드, purpose 표시, Skills API | 완료 |
| Phase 2 | 추가 원인 시나리오, diagnostics 보강, 지식 작성·상태 변경 계약 설계 | 지식 조회·검토·활성화 UI | 미착수 |
| Phase 3 | 폐쇄망 Milvus 색인, 비정형 문서용 real RAG | 출처와 검증 상태 표시 보완 | 미착수 |

완료 이력은 [백엔드 계획](../backend/plan/260914-domain-knowledge-plan.md)과
[프론트 계획](../frontend/plan/260914-domain-knowledge-plan.md)에 보존한다.

## 유지할 계약

- `knowledge/` YAML은 서비스와 Agent tool이 공유하는 source of truth다.
- KPI가 참조하는 table·recipe와 diagnostics 대상은 정합성 테스트를 통과해야 한다.
- `describe_table` 없이 SQL을 작성하지 않으며 SQL은 읽기 전용 guard를 통과한다.
- `draft` 지식으로 계산한 답변은 미검증 기준임을 사용자에게 알린다.
- 지식 조회 API는 작성 기능의 권한 모델이 확정될 때까지 읽기 전용이다.

## 다음 완료 조건

- 작성·검토·활성화의 의미와 권한이 상위 요구사항으로 확정된다.
- 추가 원인 시나리오가 시드 데이터와 E2E 기대 진단을 함께 정의한다.
- 실제 테이블·KPI·단위가 현업 검토를 거쳐 `verified`로 전환된다.
- Phase 3는 폐쇄망에서 사용 가능한 Milvus와 임베딩 모델을 확정한 뒤 착수한다.
