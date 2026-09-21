# Services 작업 지침

`backend/services`는 route·agent·tool에서 호출하는 업무 로직과 저장소,
mock/real provider 경계다. 상위 `../AGENTS.md`의 계층·읽기 전용·폐쇄망
규칙을 함께 따른다.

## Logging 계약

- `services/` 아래 Python 코드를 수정할 때는 영향을 받는 공개 실행 경로의 logging이
  함께 유지되는지 반드시 확인한다. 새 service 동작을 설명하는 문서를 수정할 때도
  시작·완료·실패와 주요 분기 중 무엇을 기록할지 logging 기준을 함께 명시한다.
- 새로 추가하거나 수정하는 공개 service 작업은 시작, 정상 완료, 실패를
  로그로 남긴다. 공통 경계 로그는 `service_logging.logged_service_operation`을
  우선 사용한다.
- 완료 로그에는 작업명과 소요 시간을 남긴다. 최상위 작업은 `INFO`, 그 안에서
  호출되는 service 작업은 `DEBUG`로 남겨 기본 로그의 중복을 막는다. 업무 흐름을
  판별하는 데 필요한 주요 분기·건수·상태는 각 service module에서 별도 `INFO`로 남긴다.
- 예상 가능한 업무 거절·검증 실패는 `WARNING`, 예상하지 못한 장애는 `ERROR`로
  남긴다. 예외 메시지와 stack trace는 민감 정보가 없음을 보장할 수 있을 때만
  제한적으로 추가하고, 기본 경계 로그에는 비식별 오류 유형만 기록한다.
- 예외 대신 `{"status": "error"}`를 반환하는 기존 계약도 성공으로 기록하지 않고
  공통 helper가 업무 오류 `WARNING`으로 남기게 유지한다.
- SQL 원문, 질문·문서 본문, 결과 행, access scope/cookie, API key·인증 정보,
  사내 URL, 로컬 절대 경로는 로그에 남기지 않는다. 필요하면 건수,
  boolean, 공개 상태, 비식별 오류 유형만 기록한다.
- 같은 작업을 wrapper와 하위 구현에서 중복 로깅하지 않도록 외부에서
  관찰할 공개 경계에 로깅 책임을 둔다.
- `print`를 사용하지 말고 module logger 또는 공통 logging helper를 사용한다.

## 변경 검증

- 새 service 경계와 실패 경로를 추가하면 `caplog` 또는 logger mock으로
  시작·완료·실패 로그와 민감 정보 비노출을 검증한다.
- mock과 real service의 공개 함수 시그니처와 반환 형태를 유지한다.
- 검증은 `backend/`에서 `.venv/bin/python -m pytest -q`로 실행한다.
