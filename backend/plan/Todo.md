# Backend 할 일과 아이디어

새 작업과 떠오른 아이디어를 이곳에 기록한다. 착수한 작업의 결정·진행 상황은 [진행 중](InProgress.md), 완료 결과는 [완료 이력](History.md)으로 옮긴다. 각 workspace의 범위와 현재 계약은 진행 중 문서를 따른다.

## 해야 할 일


### P1

- [ ] **후속질문 동적 생성**: 성공한 `done`에 2~4개 제안을 선택적으로 추가한다.
  각 제안은 1~120자, 중복·빈 문자열 없이 한국어 질문 문구로 제한한다. 데이터에
  종속된 답이나 비공개 추론은 생성하지 않는다. 파싱·생성 실패는 응답 전체를 실패시키지
  않고 `suggestions`를 생략하거나 빈 배열로 종료한다. 오류·취소 turn에는 붙이지 않는다.
  소비자 파서는 이미 준비돼 있다.

### P2

- [ ] 실제 업무 데이터로 생산 부진 원인 scenario와 KPI·join·집계 정의를 현업
  검토하고 verified 상태를 갱신한다.
- [ ] 서버 처리 시간 공개 필요성, 측정 의미와 비용을 검토한다. 클라이언트 관측
  시간과 혼동되는 값은 추가하지 않는다.
- [ ] Result Store 후속 재집계와 저장 backend 교체 필요성을 검토한다.

### P3

- [ ] 로컬 vector DB 기반 문서 색인·검색·출처 반환 RAG를 구현한다.
- [ ] `services/production`에 실제 사내 DB·RAG·simulation provider를 연결한다.
  인터페이스·설정 가드레일(`common_sql_client.py`·`milvus_client.py`·
  `simulation_api_client.py` 스텁과 env var 자리는 선행 준비를 마쳤다(2026-09-23).
  `/anthropic` 경로와 `LLM_PROVIDER=local` 설정은 유지하되 프록시 본문은 비워
  두었으며, 폐쇄망에서 사용할 구현을 반입한 뒤 채운다. 남은 작업은 실제 pntfp
  HTTP 호출 로직 이식이다.
- [ ] 실제 폐쇄망 DB 스키마·RAG 문서 구조 정보를 확보하면
  `scripts/generate_mock_database.py`의 `SEGMENTS`(세그먼트 규모)와
  `scripts/generate_mock_documents.py`의 문서 주제·카테고리를 재검토해 실제
  구조와의 유사도를 높인다. 테이블/컬럼명은 실제 스키마가 크게 다르면 그때
  다시 정한다.
- [ ] 인증 principal, 영속 대화·분기 저장과 실제 모델 설정 조회 계약을 별도
  계획으로 설계한다. 착수 전 실제 인증 principal과 폐쇄망에 반입 가능한 저장소를
  정하고, 소유권·재시작 후 fork·보존 기간·24시간 Result Store TTL이 지난 결과 참조의
  표시 정책을 함께 결정한다. 현재 임시 principal을 보안 경계로 사용하지 않는다.

## 아이디어

- 아직 기록된 아이디어 없음. 검토 전 생각은 이곳에 적고, 작업으로 확정되면 위 목록으로 옮긴다.
