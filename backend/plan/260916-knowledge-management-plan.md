# 지식 관리 Backend 실행 계획

**상태: 이번 범위 구현·검증 완료 (2026-09-16). 상위: [공유 계약](../../plan/260916-knowledge-management-plan.md).**
Frontend는 조회·문서 API가 준비된 후 연결한다.

1. document store/schema/API: SQLite 불변 본문 버전과 상태 이력, 검토·활성화·보관 및 revision 충돌 검증.
2. 검색/tool catalog: 공통 local 검색과 SDK 정의 재사용. 한글/빈 결과/검토본만 노출 테스트.
3. 진단: YAML diagnostics·recipe 및 테스트 전용 관계 누락/dataset 혼합/중복 집계 검증.
4. 기본 pytest 및 실제 provider 없이 fake 관통 검증. 운영 백업·복구 문서 반영.

## 검증 기록

- Backend: 기본 pytest 248개 통과, provider E2E 6개는 기본 실행에서 제외.
- 신규 실제 provider E2E: `python -m pytest -m e2e -q tests/test_e2e_knowledge.py` 1개 통과.
- Frontend: npm test 52개, build, lint 통과. 기존 fast-refresh 경고 13개와 번들 크기 안내 유지.
- 브라우저: 기존 chat lifecycle 11개와 knowledge workspace 4개 통과.
- 실제 UI에서 텍스트 등록→검토→활성화→fake 검색→인용 버전 열기 확인.
- 400px에서 목록/상세 전환, 읽기 전용 인용, 가로 넘침 0px 확인.
- 격리 SQLite로 동시 변경 충돌·재시작·백업 복구·비활성/보관 검색 제외 검증.
- Milvus·업로드·실제 생산 부진 원인 분석은 후속. 새 diagnostics는 현업 검토 대기.
