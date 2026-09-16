# 공개 실행 안내 가독성·지속성 실행 계획

**상위 계획:** `../../plan/260916-reasoning-readability-plan.md`

**상태:** 완료

- [x] 초기 요청 분석 상태의 글자 크기·대비·spinner 접근성을 개선한다.
- [x] 일반 Tool 직전 공개 텍스트를 해당 Tool 실행 중 metadata로 유지한다.
- [x] 안내를 현재 Tool 행 바로 위에 배치하고 ToolGroup 상단 파란 블록을 제거한다.
- [x] Tool 결과·다음 공개 출력·종료 경계에서 오래된 안내를 교체하거나 제거한다.
- [x] 공개 진행 단계와 ToolGroup 진행 헤더의 가독성을 함께 맞춘다.
- [x] 요청 분석과 ToolGroup의 활성 아이콘을 실행 중 계속 회전시킨다.
- [x] 상태 변환, 실제 AssistantMessage DOM, build와 lint를 검증한다.

내부 Claude SDK thinking은 계속 Backend adapter에서 폐기하며, 화면에는 기존
`AgentEvent.text`로 공개된 문구만 표시한다.

검증: 54 tests passed, production build passed, lint 0 errors(기존 registry
Fast Refresh 경고 13개), 브라우저 lifecycle 11개 회귀와 실제 앱 초기 진행
상태의 `text-ui`·`text-ink-2` 적용 확인.
