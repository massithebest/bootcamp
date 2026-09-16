# 공개 실행 안내 가독성·지속성 계획

**상태: 완료 · 2026-09-16**

## 문제

- 첫 응답 전 `요청 분석 중`이 12px 저대비 텍스트와 shimmer로 표시되어 읽기 어렵다.
- 모델이 일반 Tool 호출 직전에 공개 `text` 이벤트로 보낸 작업 안내가 Tool 호출과
  동시에 최종 답변 필터에서 제거되어 사용자가 내용을 확인하기 어렵다.
- Claude SDK의 비공개 thinking과 공개 업무 안내를 혼동해서는 안 된다.

## 범위와 계약

- Backend `AgentEvent` 계약은 변경하지 않는다. Adapter가 허용한 공개 `text`만
  사용하고 thinking/signature/tool input delta는 계속 폐기한다.
- 실행 중인 최신 일반 Tool 직전의 공개 텍스트를 Frontend metadata의
  `progressText`로 전달한다. Tool 결과·다음 공개 텍스트·종료에서 제거하고,
  새 일반 Tool이 시작되면 그 직전 문구로 교체한다.
- `progressText`는 ToolGroup 상단 강조 블록이 아닌 현재 실행 Tool 행 바로 위에
  일반 텍스트로 표시하며 최종 답변에는 남기지 않는다.
- 초기·단계 진행 텍스트는 프로젝트의 `text-ui`, `text-ink-2` 이상을 사용하고
  spinner와 문구를 함께 제공한다.

## 완료 조건

- `요청 분석 중`과 실행 단계가 기존보다 크고 진하게 보인다.
- 공개 Tool 직전 안내가 해당 Tool 실행 중 사라지지 않는다.
- 안내는 현재 실행 Tool 바로 위에만 보이고 상단 파란 블록은 보이지 않는다.
- 다음 공개 출력이나 종료 후 오래된 안내가 남지 않는다.
- 요청 분석·Tool 실행·응답 작성 중에 헤더 좌측 아이콘이 계속 회전한다.
- 내부 reasoning은 노출하지 않으며 Frontend test/build/lint와 브라우저 회귀가 통과한다.

## 완료 기록

- 공개 Tool 직전 텍스트를 해당 Tool 실행 중에만 `progressText`로 유지하고,
  Tool 결과·다음 출력·종료에서 교체 또는 제거하도록 runtime 변환을 보완했다.
- 상단 파란 `진행 안내` 블록을 제거하고, 안내 문구를 현재 Tool 행 바로
  위에 배치했다. 실행 헤더의 좌측 아이콘은 활성 상태 동안 계속 회전한다.
- `요청 분석 중`과 ToolGroup 헤더의 회전 아이콘을 1px 광학 보정해 한글
  라벨의 중심선과 맞췄다.
- 초기 상태, ToolGroup 헤더, 공개 실행 단계를 semantic token 기반 13px 계열로 높이고
  shimmer 대신 고정 대비 텍스트와 상태 spinner를 사용했다.
- 상태 변환 단위 테스트와 실제 AssistantMessage DOM 회귀 케이스를 추가했다.
- Frontend 54개 테스트, production build, lint(오류 0건·기존 Fast Refresh 경고
  13건), 브라우저 lifecycle 11개 회귀와 실제 앱 초기 진행 화면을 검증했다.
