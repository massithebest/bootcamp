# 누적 미커밋 변경 통합 검토

**상태: 완료. 마지막 갱신: 2026-09-16.**

## 목적과 범위

assistant-ui Elements, 공개 스트리밍과 Tool trace, standalone 표·차트,
TanStack Table, 조회 1,000행/표시 100행 및 선택 인자 스키마 변경을 하나의
기능 집합으로 검토한다. staged·unstaged·untracked를 모두 확인하며 사용자
변경을 보존한다. 검증 후 하나의 Conventional Commit으로 정리하고 push하지 않는다.

## 공유 계약과 파트별 할당

기존 [메시지 순서 계획](260916-tanstack-table-message-order-plan.md),
[대화형 표 계획](260916-interactive-table-tool-ui-plan.md),
[Tool trace 계획](260916-nested-tool-reasoning-plan.md),
[선택 인자 계획](260916-optional-catalog-tool-schema-plan.md)의 계약을 유지한다.

- Backend: [표 실행 계획](../backend/plan/260916-interactive-table-tool-ui-plan.md)의
  자동 보완 조건·중복 방지와 MCP 스키마를 검증한다.
- Frontend: [메시지 순서 실행 계획](../frontend/plan/260916-tanstack-table-message-order-plan.md)의
  후속 조회 시 기존 표현 보존, 도구 종료 표시와 표 접근성을 보완한다.
- Result Store, 시각화 API, mock/real 공개 함수, SQL 읽기 전용 경계는 유지한다.
  real 서비스는 기존과 같이 미구현 스텁이며 운영 연결 검증은 별도다.

## 발견 사항과 조치 (심각도 순)

1. **P1 — 이미 표시한 결과 소실:** 마지막 일반 Tool 뒤만 잘라 렌더링하므로
   표·차트 뒤 추가 조회 시 앞선 표현과 해석이 사라졌다. 표·차트가 포함된
   문맥 구간과 마지막 답변 구간을 보존하고 일반 Tool만 실행 그룹으로 모은다.
2. **P2 — 코드 예제 소실:** 중복 Markdown 표 제거가 코드 펜스 내부까지
   삭제했다. backtick/tilde 펜스를 보존한다.
3. **P2 — 잘못된 완료 표시:** 결과 전에 중단·실패한 Tool이 완료로 표시됐다.
   결과 없는 종료는 미완료와 종료 안내로 표시한다.
4. **P2 — 불필요한 자동 Tool 호출:** 표 요청 감지가 목표·지표·대표와 stable을
   오인했다. 단어 경계를 확인하며 기존 성공 표 뒤 자동 호출이 중복되지 않는
   회귀 테스트를 추가했다.
5. **P2 — 초기 배포 누락:** 폐쇄망 가이드에 mock SQLite 생성 절차가 없었다.
   원본 TSV로 DB 생성 및 SQL·표·차트 성공 payload 확인을 추가했다.
6. **P3 — 중복 DOM ID:** 같은 result_id의 표를 재표시하면 페이지 크기 레이블이
   중복됐다. 렌더 인스턴스마다 React useId로 연결한다.

## 검증 및 완료 조건

- Backend `python -m pytest -q`: 240 passed, 5 deselected. 외부 provider E2E는 제외.
- Frontend `npm test`: 49 passed. `npm run build` 성공, `npm run lint` 오류 0.
- Chromium lifecycle harness 11개 PASS. 실제 App + 별도 Fake FastAPI에서 질문 전송,
  Tool 성공, text→table→text→chart→text 순서와 Recharts SVG 확인.
- 제어된 100행 SSE: 숫자 정렬 asc/desc/none, 검색, 다음 페이지, 페이지 크기
  10/25/50/100, 스트리밍 중 페이지 유지, 후속 조회 뒤 기존 표 유지와 오류 표시 확인.
- desktop 세 pane 헤더 높이 64px 일치, 400px pane 자동 접힘·컴포저·가로 넘침 없음.
  실제 App 검증 중 브라우저 page error 및 외부 리소스 요청 없음.
- package/lockfile 일치 및 설치 트리 확인. 신규 의존성 설치 스크립트 없음.
  Python 의존성 변경 없음. 비밀값 패턴·상대 문서 링크·커밋 파일 목록 확인.
- untracked 파일을 stage한 뒤 드러난 공백·파일 끝 빈 줄 경고를 정리했다.
  `git diff --check`, `git diff --cached --check`와 최종 staged diff 점검을 완료했다.

## 남은 경고와 검증 한계

- 검토 시작 시부터 존재한 Fast Refresh 경고 13개와 500kB 초과 번들 경고 유지.
  이번 검토 수정에서 새 경고는 추가하지 않았다. 반입한 공식 소스의 미사용
  기능 파일은 요청된 CLI 반입 이력이므로 임의 삭제하지 않는다.
- 사내 Nexus의 패키지·전이 의존성 확보, 실제 LLM/provider, real 서비스와
  Windows 폐쇄망 설치는 이 환경에서 검증하지 않았다.
- 루트에서 잘못 실행한 `npm test`는 package.json 부재로 실패했으며 올바른
  `frontend/`에서 다시 실행해 통과했다. 제품 결함은 아니었다.
