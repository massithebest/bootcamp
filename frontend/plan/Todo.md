# Frontend 할 일과 아이디어

새 작업과 떠오른 아이디어를 이곳에 기록한다. 착수한 작업의 결정·진행 상황은 [진행 중](InProgress.md), 완료 결과는 [완료 이력](History.md)으로 옮긴다. 각 workspace의 범위와 현재 계약은 진행 중 문서를 따른다.

## 해야 할 일


### P2

- [ ] 실제 screen reader와 긴 대화 성능을 운영 환경에서 검증한다.
- [ ] 인증 principal이 연결되면 임시 사용자 선택기와 `lib/knowledge-user.ts`를 제거하고
  `GET /api/me`만으로 권한을 표시한다.
- [ ] 실제 모델 설정 API가 제공될 때 현재 비활성 모델·추론 강도 control의 표시
  정책을 재검토한다. API가 없으면 비활성 안내를 유지한다.
- [ ] 결과 필터·재집계 API가 제공될 때 Result Store 후속 탐색 UX를 별도 계획한다.

### P3

- [ ] 영속 대화·분기 API와 인증 principal이 제공될 때 `lib/agent-threads.ts`의 메모리
  `RemoteThreadListAdapter`·`ThreadHistoryAdapter`를 실제 저장소 adapter로 교체한다.
- [ ] 실제 사내 서비스 환경에서 SQL·RAG·simulation 오류, 장시간 streaming과
  재연결을 관통 검증한다.

## 아이디어

- 아직 기록된 아이디어 없음. 검토 전 생각은 이곳에 적고, 작업으로 확정되면 위 목록으로 옮긴다.
