# assistant-ui Elements 반입 안내

이 폴더는 assistant-ui registry와 공식 Elements를 복사한 뒤 React 18, 현재 runtime,
한국어 UI와 프로젝트 semantic token에 맞게 조정한 소스다. npm 패키지를 올려도
자동 갱신되지 않는다.

## 유지 원칙

- 공용 채팅 primitive와 접근성 동작은 upstream 문서와 설치된 타입을 기준으로 한다.
- Backend에 없는 attachment·dictation·Cloud 기능과 미연결 action은 추가하지 않는다.
- Thread·Composer·Tool UI는 프로젝트의 SSE `ChatModelAdapter`와 공개 `AgentEvent`
  계약을 유지한다. 모델 thinking은 렌더링하지 않는다.
- copied source를 갱신할 때는 upstream 출처·라이선스와 프로젝트 변경점을 diff로
  확인하고 `npm test && npm run build && npm run lint`를 실행한다.

현재 실행 방법은 [Frontend README](../../../../README.md), 디자인 기준은
[assistant-ui 디자인 문서](../../../../docs/assistant-ui-design.md), 적용 결정은
[현재 계약과 UI 결정](../../../../plan/InProgress.md)을 따른다. MIT 고지는
[LICENSE](../LICENSE)에 있다.
