# 지식 관리 Frontend 실행 계획

**상태: 이번 범위 구현·검증 완료 (2026-09-16). 상위: [공유 계약](../../plan/260916-knowledge-management-plan.md).**
Backend API 계약 준비 후 연결하며 더미 저장 기능을 만들지 않는다.

1. API/types: 응답 검증과 안전한 오류 처리, 조회 취소.
2. 조회 패널: 지식·도구·Skills, 설명/입력/출처/상태, 관리 상세 연결.
3. 관리: 목록·필터·본문 편집·검토 비교·활성화·이력·미저장 이동 처리.
4. 셸: 좌측 관리 메뉴, Thread 마운트 유지, 입력/스트리밍/스크롤 보존, 인용 버전 이동.
5. npm test/build/lint 및 브라우저 등록→검색 관통·좁은 화면·키보드 검증.

## 검증 기록

- Backend: 기본 pytest 248개 통과, provider E2E 6개는 기본 실행에서 제외.
- 신규 실제 provider E2E: `python -m pytest -m e2e -q tests/test_e2e_knowledge.py` 1개 통과.
- Frontend: npm test 52개, build, lint 통과. 기존 fast-refresh 경고 13개와 번들 크기 안내 유지.
- 브라우저: 기존 chat lifecycle 11개와 knowledge workspace 4개 통과.
- 실제 UI에서 텍스트 등록→검토→활성화→fake 검색→인용 버전 열기 확인.
- 400px에서 목록/상세 전환, 읽기 전용 인용, 가로 넘침 0px 확인.
- 격리 SQLite로 동시 변경 충돌·재시작·백업 복구·비활성/보관 검색 제외 검증.
- Milvus·업로드·실제 생산 부진 원인 분석은 후속. 새 diagnostics는 현업 검토 대기.

## Inspector 가독성 후속 (2026-09-16)

**상태: 구현·검증 완료.** 사용자 요청에 따라 도구 상세의 입력 명세를 제거하고,
Skills disclosure 버튼과 raw Markdown 출력을 읽기 전용 정적 문서 표현으로 대체한다.
Backend 계약은 변경하지 않는다.

- 도구: 이름·상태·설명·결과 형태만 표시하고 `input_schema` JSON은 숨긴다.
- Skills: 목록의 각 항목을 항상 표시하고 h3 이름 아래 Markdown 제목·목록·코드를
  h4 이하 의미 구조로 렌더링한다. 임의 HTML은 렌더링하지 않는다.
- 레이아웃: 구분선·좌측 룰·여백을 늘리고 1280px 이상 Inspector는 23rem,
  그 아래와 overlay는 20rem을 유지한다.
- 검증: 단위/SSR, build/lint, 실제 API 화면, 1280px/1440px 및 좁은 overlay 브라우저 회귀.

검증 결과: `npm test` 67개 통과, build 성공, lint 오류 0·기존 Fast Refresh 경고
13개. Workbench 브라우저 회귀는 1280px와 400px에서 각각 9개 통과했다.
실제 API를 연결한 1440px 화면에서 Inspector 368px, 가로 overflow 0px,
Skills 버튼 0개, raw Markdown 미노출, h3→h4→h5 위계와 도구 schema 미노출을 확인했다.
기존 500kB 이상 bundle 경고는 유지된다.

## Skills disclosure 복원 (2026-09-16)

**상태: 구현·검증 완료.** 사용자 후속 요청으로 스킬별 드롭다운을 복원한다.
접힌 상태에는 이름·사용 가능 상태·요약을 유지하고 선택한 상세만 lazy-load한다.
개선한 Markdown 렌더링·간격·제목 위계·Inspector 폭은 유지한다.

- 접근성: 네이티브 button, `aria-expanded`, `aria-controls`, 키보드 Enter/Space.
- 회귀: 기본 접힘, 펼침 후 API 호출과 Markdown 목록 표시, 다시 접기, 좁은 화면 overflow.

검증 결과: `npm test` 67개 통과, build 성공, lint 오류 0·기존 경고 13개.
Workbench 브라우저 9개 통과. 실제 API 화면에서 세 항목 기본 접힘, 선택 항목만
`aria-expanded=true`, `aria-controls` 연결, 펼침·재접힘, raw Markdown 미노출,
가로 overflow 0px을 확인했다. 기존 bundle 크기 경고는 유지된다.

## 2026-09-17 Inspector 스크롤바 공간 안정화

- [x] 도구·스킬·지식 tabpanel에 `scrollbar-gutter: stable`을 적용한다.
- [x] 가장 긴 Skill을 펼쳐 세로 스크롤바가 생겨도 상단 Skill 설명의 폭과 줄 수가
  바뀌지 않음을 실제 브라우저에서 확인한다.
- [x] 좁은 화면 Inspector overlay의 `absolute`·`relative` 클래스 충돌을 제거해
  pane을 열어도 Chat 폭을 압축하지 않게 한다.
