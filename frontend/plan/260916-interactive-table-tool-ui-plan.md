# 대화형 표 Tool UI — Frontend

**상태: 완료. 상위 계획: [대화형 표 계획](../../plan/260916-interactive-table-tool-ui-plan.md).**

Backend의 `prepare_table` 성공 payload 계약이 준비된 뒤 같은 이름의 render-only
Tool UI를 등록한다.

## Task

- [x] 공용 표와 Markdown 표 표시 상한을 100행으로 올린다.
- [x] `prepare_table` payload를 엄격히 파싱하고 loading/error/empty 상태를 처리한다.
- [x] 검색·열 정렬·페이지 크기 10/25/50/100·이전/다음 이동을 제공하는 접근 가능한
  대화형 표를 구현한다.
- [x] Tool을 standalone으로 등록하고 최종 답변 다음 순서에 배치한다.
- [x] 자동 보완 Tool이 텍스트 뒤에 도착해도 답변을 유지하고, 성공한 대화형 표와
  중복되는 Markdown 표만 제거한다.
- [x] 렌더·메시지 순서 테스트와 test/build/lint 결과를 기록한다.

## 완료 조건

- 최대 100행 payload 밖의 값이나 잘못된 열/행 계약은 표로 렌더링하지 않는다.
- 필터·정렬 결과 건수, 현재 페이지와 원본/표시 행 수를 사용자에게 명확히 알린다.

## 결정·실행 기록

- `prepare_table`과 `prepare_visualization`을 같은 standalone 집합으로 처리해 둘 다
  최종 설명 뒤에 호출 순서대로 배치한다. 일반 Tool은 기존 실행 과정 그룹에 남는다.
- 숫자는 숫자로 정렬하고 나머지는 한국어 locale·숫자 인식 문자열 정렬을 쓴다.
  검색·정렬·페이지 크기가 바뀌면 첫 페이지로 돌아간다.
- 자동 보완 `prepare_table` 이벤트가 답변 텍스트 뒤에 도착하는 순서를 지원한다.
  성공 payload가 있을 때만 GFM 표 블록을 제거하므로 일반 개념 비교 표는 유지된다.
- `npm test`: 44개 통과. `npm run build`: 성공. `npm run lint`: 오류 0,
  기존 Fast Refresh 경고 13개. 실제 브라우저에서 검색·정렬·페이지 이동과
  10→25 페이지 크기 전환, overlay/console error 없음까지 확인했다. Backend 재시작
  뒤 실제 Agent의 `part_1` Route 30행 응답에서도 같은 상호작용을 다시 검증했다.
