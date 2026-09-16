# 후속질문 동적 생성 — Backend

**상태: 진행 예정. 상위 계획: [후속질문 동적 생성](../../plan/260916-followup-suggestions-plan.md).**

Frontend는 `done.data.follow_up_questions`를 읽어 동적 제안 칩으로 렌더링한다.

## Task

- [ ] `services/knowledge_service.py`의 `KnowledgeKpi`, `KnowledgeRecipe`에
  `follow_up_hints: list[str] = []`를 추가한다. 로더·조회 메서드는 변경하지
  않는다(`model_dump(mode="json")`이 자동 반영).
- [ ] `knowledge/kpi/initial_wip.yaml`에 `follow_up_hints` 예시 1~2개를 추가해
  메커니즘을 증명한다.
- [ ] `agent/agent.py`에 마커 상수(`_FOLLOWUP_MARKER_START = "<!--FOLLOWUP_QUESTIONS"`,
  `_FOLLOWUP_MARKER_END = "-->"`)와 tail-buffer 헬퍼(`_advance_text_buffer`,
  `_extract_follow_up_questions`)를 추가한다. `run_agent`의 스트리밍 루프에서:
  - 마커 시작이 확정되기 전까지는 기존과 동일하게 즉시 `text` 이벤트를 yield한다
    (접두사 겹침이 있으면 확정될 때까지만 보류).
  - 마커 시작이 확정되면 이후 텍스트는 `text` 이벤트로 yield하지 않고
    `marker_buffer`에만 누적한다.
  - `response_text`(표 폴백 휴리스틱이 참조)는 마커 이전 텍스트만 누적하도록
    유지한다.
  - 루프 종료 후: 남은 `pending_tail`(마커가 아니었던 것으로 판명)은 `text`로
    flush한다. 닫히지 않은 `marker_buffer`는 조용히 버린다. `marker_buffer`가
    정상적으로 닫혔으면 `- ` 줄 단위로 파싱해 최대 4개, 빈 문자열 제거 후
    `follow_up_questions`로 확정한다.
  - non-text 이벤트가 `marker_buffer`가 열린 채로 끼어들면 마커를 포기(버림)하고
    일반 텍스트 버퍼링으로 복귀한다(코드 주석으로 명시, 별도 테스트는 선택).
  - 성공 분기의 최종 `done` yield에 `data["follow_up_questions"] = [...]`를
    추가한다. 실패 조기 종료 `done`(`data=None`)은 그대로 둔다.
- [ ] `agent/fake_runner.py`의 마지막 `done` yield에 하드코딩된
  `follow_up_questions` 리스트를 추가한다(기존 한국어 하드코딩 스타일 유지).
- [ ] `agent/agent_sdk/CLAUDE.md`에 "## 결과 검증 원칙" 다음, "## Skills" 이전
  위치로 "## 응답 마무리 — 후속 질문 제안" 섹션을 추가한다:
  - 이번 턴에 실제로 확인한 내용 근거로 2~4개 생성, 일반적 상투 질문 금지.
  - `get_kpi`/`get_recipe` 결과의 `follow_up_hints`는 맥락에 맞을 때만 참고.
  - 정확한 마커 형식(상수와 동일 문자열)을 명시.
  - 자연스러운 후속질문이 없으면 블록 자체를 쓰지 않는다.
  - `SYSTEM_PROMPT`(30줄 제한·도구명 언급 금지 규칙이 테스트로 강제됨)에는
    넣지 않고, 스킬별 종료 단계에도 중복 추가하지 않는다.
- [ ] 테스트:
  - `tests/test_agent.py`: 마커 파싱, 청크 경계 분할(마커 시작 토큰이 여러
    스트림 청크에 걸쳐 나뉘는 경우), 마커 없음, 마커 미완성(버려짐) 케이스.
    `_advance_text_buffer`/`_extract_follow_up_questions` 단위 테스트. 기존
    `done` 테스트를 확장해 `done.data["follow_up_questions"]` 검증과 어떤
    `text` 이벤트에도 마커 문자열이 섞이지 않았는지 검증.
  - `tests/test_api.py`: `test_chat_endpoint_done_event_carries_turn_id` 패턴으로
    fake runner 기반 SSE JSON 레벨 검증 테스트 추가.
  - `tests/test_prompt_consistency.py`: CLAUDE.md가 `agent.py`의 마커 상수를
    그대로 포함하는지 검증하는 테스트 추가(상수를 import해 문자열 이중 정의
    방지).
  - `event_adapter.py` 관련 기존 테스트는 변경하지 않는다(어댑터 자체는 무변경).
  - 표 폴백(`_needs_table_fallback`) 관련 기존 테스트가 `response_text`에
    의존하므로 회귀 없는지 재확인한다.
- [ ] 전체 `python -m pytest -q` 결과를 기록한다.

## 완료 조건

- 모델이 마커 형식을 지키지 못해도 원문이 `text` 이벤트로 노출되지 않는다
  (파싱 실패 시 `follow_up_questions`는 빈 배열).
- `done.data.follow_up_questions`는 성공한 턴에서만 채워지고, 실패 조기 종료
  `done`에는 포함되지 않는다.
- mock(`fake_runner.py`)과 real 경로의 `done` 결과 형태가 동일하다.

## 결정·실행 기록

_구현 후 기록._
