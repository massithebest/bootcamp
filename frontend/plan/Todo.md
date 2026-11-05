# Frontend 할 일과 아이디어

새 작업과 떠오른 아이디어를 이곳에 기록한다. 착수한 작업의 결정·진행 상황은 [진행 중](InProgress.md), 완료 결과는 [완료 이력](History.md)으로 옮긴다. 각 workspace의 범위와 현재 계약은 진행 중 문서를 따른다.

## 해야 할 일


### P2

- [ ] 실제 screen reader와 긴 대화 성능을 운영 환경에서 검증한다.
- [ ] 인증 principal이 연결되면 임시 사용자 선택기와 `lib/knowledge-user.ts`를 제거하고
  `GET /api/me`만으로 권한을 표시한다.
- [ ] 브라우저 회귀 검사의 간헐 실패를 고친다: `knowledge-browser.html` "button missing: 텍스트 지식 등록", `workbench-browser.html` "Inspector scrollbar
  changed text width". 메뉴 표시·폭 측정의 타이밍 의존으로 의심되며(미확인), `npm test`에 포함되지 않아 자동으로 드러나지 않는다.
- [ ] 모델 선택·추론 강도 조절 API가 제공될 때 입력창의 읽기 전용 모델 이름을 선택 control로 바꾼다. 허용 모델 목록과 모델별 추론 강도 지원을
  먼저 확인한다(`GET /api/model-info`는 표시 이름만 제공).
- [ ] 결과 필터·재집계 API가 제공될 때 Result Store 후속 탐색 UX를 별도 계획한다.

### P3

- [ ] 영속 대화·분기 API와 인증 principal이 제공될 때 `lib/agent-threads.ts`의 메모리
  `RemoteThreadListAdapter`·`ThreadHistoryAdapter`를 실제 저장소 adapter로 교체한다.
- [ ] 실제 사내 서비스 환경에서 SQL·RAG·simulation 오류, 장시간 streaming과
  재연결을 관통 검증한다.

## 아이디어

- 아직 기록된 아이디어 없음. 검토 전 생각은 이곳에 적고, 작업으로 확정되면 위 목록으로 옮긴다.
