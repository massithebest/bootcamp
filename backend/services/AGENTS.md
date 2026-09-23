# Services 작업 지침

`services/`는 업무 로직, 저장소와 mock/production provider 경계다. 상위 지침의
계층·읽기 전용·폐쇄망 원칙을 따른다.

- 공개 service 작업은 시작·완료·실패와 소요 시간을 기록한다.
  `service_logging.logged_service_operation`을 우선 사용하고 중첩 작업은 DEBUG로 둔다.
- 업무 거절·검증 실패는 WARNING, 예상하지 못한 장애는 ERROR로 기록한다.
  오류 dict 반환도 성공으로 기록하지 않는다.
- SQL·질문·문서 본문·결과 행·scope/cookie·비밀값·사내 URL·절대 경로는 로그에
  남기지 않는다. 외부 관찰 경계 한 곳에서만 기록하고 `print`를 쓰지 않는다.
- 변경 시 mock/production 공개 계약과 로그의 성공·실패·민감정보 비노출을 테스트한다.
