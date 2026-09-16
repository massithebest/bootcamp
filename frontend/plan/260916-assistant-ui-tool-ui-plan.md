# assistant-ui Tool UI 기반 차트 표시 — Frontend

**상태: 완료. 상위 계획: [Tool UI 차트 계획](../../plan/260916-assistant-ui-tool-ui-plan.md).**

Backend는 기존 `prepare_visualization` 결과 계약을 유지하고 신규 마커 생성만
중단한다. 프론트는 현재 FastAPI SSE와 `useExternalStoreRuntime`을 유지한다.

## Task

- 렌더링 전용 `prepare_visualization` toolkit을 루트 Provider에 등록한다.
- 기존 ID 기반 조회·검증·재시도 UI를 Tool UI와 마커가 함께 쓰도록 분리한다.
- 차트 Tool만 standalone으로 분리하고 최종 설명 다음에 배치한다.
- 준비·성공·오류·중단 상태와 잘못된 ID를 검증한다.
- 기존 마커 회귀와 toolkit·메시지 순서를 테스트하고 test/build/lint를 실행한다.

## 완료 조건

- 새 패키지와 전송 계약 변경 없이 검증된 차트가 Tool 결과에서 표시된다.
- 다른 Tool 카드와 기존 마커 호환이 유지된다.

## 결정·실행 기록

- plain toolkit의 `type: "backend"` renderer를 사용해 compiler·AI SDK 의존성을
  추가하지 않았다. Tool UI와 과거 marker는 ID 기반 조회 renderer를 공유한다.
- 같은 `result_id`의 후속 성공이 있으면 앞선 실패 Tool part를 변환 단계에서
  제외하고, 의도적으로 만든 서로 다른 성공 차트는 모두 유지한다.
- `npm test`: 39개 통과. `npm run build`: 성공. `npm run lint`: 오류 0,
  기존 Fast Refresh 경고 13개 유지.
- 실제 브라우저에서 실행 과정 접힘, 최종 설명 뒤 차트, 보정 실패 숨김, 차트 1개,
  marker 코드 0개, console/page error와 Vite overlay 없음까지 확인했다.
