# 홈페이지형 Composer·Reasoning Frontend 실행 계획

**상태: 완료. 마지막 갱신: 2026-09-16.**

- 상위: [공통 계획](../../plan/260916-assistant-ui-streaming-plan.md)
- 상대 파트: [Backend 계획](../../backend/plan/260916-assistant-ui-streaming-plan.md)

## Tasks

1. PromptLibrary 버튼/요소와 키 안내를 제거한다.
2. 빈 화면을 제목 → 둥근 Composer → suggestion pill 순으로 배치하고 실행 중
   Composer는 viewport 하단에 유지한다.
3. textarea 자체 focus outline을 제거하고 Composer 외곽 focus ring 하나만
   표시한다. 다른 전역 키보드 focus 표시는 유지한다.
4. 공개 status를 설치된 assistant-ui Reasoning disclosure에 연결한다.
   스트리밍 중 자동으로 열리고 완료 후 접히며 오류·취소 상태를 보존한다.
5. 답변 text delta, Markdown, tool 결과, 편집·재생성·중단·스크롤 회귀를 검증한다.

## 실행·검증 기록

- PromptLibrary 소스·버튼과 키 안내를 제거했다. 시작 화면의 예시는 compact
  `ThreadPrimitive.Suggestion` pill로 Composer 아래에 배치했다.
- 빈/대화 중 Composer를 분리 배치하고 동일 runtime draft를 사용했다.
  textarea에만 focus outline을 끄고 form 외곽 focus 표시를 유지했다.
- AgentPlan 기반 공개 단계 UI를 ReasoningRoot/Trigger/Content/Text 조합으로
  교체했다. 내부 reasoning이라는 표현 없이 공개 업무 단계만 렌더링한다.
- 테스트 30개, build, lint 오류 0(기존 경고 13), lifecycle 10개 통과.
- Chromium fixture에서 제거 문구, 단일 focus 테두리, Reasoning 자동 펼침/접힘,
  text delta 누적과 streaming cursor, desktop·400px, 외부 요청·page error 0 확인.
- 기존 전체 상호작용 fixture와 긴 응답 scroll 보존 회귀도 통과했다.
